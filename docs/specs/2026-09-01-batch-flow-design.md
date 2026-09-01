# 批量选品 · 批量编辑 · 批量上架 设计文档

日期：2026-09-01
状态：已评审待实现

## 一、背景与目标

已有单商品全流程技能（选品→1688采集→认领→类目→编辑补齐→定价→发布→验证）
和单商品编排 skill `tiktok-shop-select-and-publish`。本设计将全流程批量化：
一句话「批量选品上架」触发，一次处理 N 个商品。

## 二、需求（已确认）

| 维度 | 决策 |
| --- | --- |
| 确认粒度 | 阶段整批确认（认领 / 改价 / 发布 各确认一次） |
| 选品来源 | 商品机会数据自动打分选 Top N（默认 N=5） |
| 1688 采集 | 全自动批量采集（选品后逐个搜货源 + fetch_item 批量采集） |
| 定价 | 逐品选档（整批清单里每品三档价，逐个选档后一次性确认） |

## 三、架构

新增 2 个产物，复用 6 个现有能力。

**新增**

- `miaoshou-erp-tiktok-bulk-atomic-edit`（批量原子编辑技能）：
  `scripts/bulk_edit.py` 循环「详情→改字段→保存」。
- `tiktok-shop-batch-flow`（批量编排 skill）：
  触发词「批量选品上架」「帮我批量选品并上架」「批量上架 N 个品」。

**复用**

| 环节 | 现有能力 |
| --- | --- |
| 选品 Top N | `tiktok-shop-opportunity-selection/scripts/rank_opportunities.py` |
| 1688 批量采集 | `miaoshou-erp-source-import`（fetch_item 批量）+ 浏览器搜货源 |
| 批量认领 | `miaoshou-erp-product-claim/scripts/claim_to_platform.py batch-claim` |
| 定价计算 | `mss-vn-pricing/scripts/vn_pricing.py` |
| 批量发布 | `miaoshou-erp-tiktok-product-publish/scripts/tiktok_publish.py publish --detail-ids` |
| 批量验证 | 同上 `publish-log` |

## 四、批量编辑脚本 bulk_edit.py

- 输入：商品清单 JSON，每项含 `detailId` + 目标字段（价格/库存/重量/
  尺寸/尺码表 URL/属性）。
- 处理：逐商品 `get_shop_collect_item_info` 拿各自 `ossMd5` → 深拷贝
  `shopCollectItemInfo` 只改目标字段 → `save_shop_collect_item_info`
  回传各自 `ossMd5`。
- 输出：逐商品结果（成功/失败/跳过 + 失败原因），部分失败不中断。
- 复用 `build_edit_payload.py` 的深拷贝与改字段逻辑，避免重复实现。

## 五、编排流程 7 步 + 3 确认点

| 步 | 动作 | 确认 |
| --- | --- | --- |
| 1 | 选品 Top N（默认 5） | 自动 |
| 2 | 1688 全自动搜货源 + 批量采集到公共箱 | 自动 |
| 3 | 批量认领到 TikTok 店铺 | ✅ 整批确认 |
| 4 | 批量类目匹配 + 补齐（服装：尺码表/材质/包装） | 自动 |
| 5 | 批量定价（整批清单逐品选档） | ✅ 整批确认 |
| 6 | 批量保存（bulk_edit.py） | 并入第 5 步确认 |
| 7 | 批量发布 | ✅ 整批确认 |
| 8 | publish-log 批量验证 | 自动 |

## 六、边界与错误处理

- 服装/非服装分流：服装类目走尺码表 + 必填材质补齐，非服装跳过尺码表。
- 1688 搜不到货源：该品标记「跳过」，其余继续。
- 部分失败：逐品报告成功/失败/跳过，不整体中断。
- 写操作（认领/保存/发布）三个写点整批确认后才执行。

## 七、验收标准

- 一句话「帮我批量选品并上架」能触发编排 skill。
- 选品输出 Top N 清单（含标题/潜力分/类目）。
- 1688 批量采集成功拿到 N 个公共箱 detailId。
- 认领/改价/发布三个阶段各出整批清单等确认。
- 发布后 `publish-log` 能批量核对 N 个品状态。
