---
name: tiktok-shop-select-and-publish
description: 编排型技能：一句话跑完「选品→1688采集→认领→类目→编辑补齐→定价→发布→验证」完整流程，每个写操作（认领/改价/发布）都停下来等用户确认。Invoke when 用户说"帮我选一件商品并上架"、"选个品上架"、"一句话选品上架"、"自动选品并上架"、"从选品到上架一条龙"、"帮我选品上架到TikTok"。
---

# TikTok 选品到上架 全流程编排

一句话触发：**「帮我选一件商品并上架」**。

本技能是编排器（orchestrator），本身不写业务逻辑，按固定顺序加载并调用下面的子技能，把「选品 → 上架」串成一条链。**每个写操作都停下来等你确认**，不会自动冲到底。

## 触发词

- 帮我选一件商品并上架
- 选个品上架 / 一句话选品上架
- 自动选品并上架到 TikTok
- 从选品到上架一条龙

## 前置条件（缺一则先向用户要）

- 妙手 AppKey/AppSecret（各子技能 `resources/config.json`，已配置则跳过）
- TikTok 卖家中心登录 cookie（第 1 步选品抓「商品机会」需要）
- 目标站点与店铺（默认越南站，店铺用 `miaoshou-erp-shop-query` 查）

## 编排流程（8 步）

| 步 | 动作 | 子技能 | 是否确认 |
|---|---|---|---|
| 1 | 抓商品机会数据选品 | `tiktok-shop-opportunity-selection` | 自动 |
| 2 | 1688 找货源采集到公共箱 | `mss-1688-sourcing` | 自动 |
| 3 | 认领到 TikTok 店铺 | `miaoshou-erp-product-claim` | ✅ 确认 |
| 4 | 类目匹配 | `miaoshou-erp-tiktok-category-recommend` | 自动 |
| 5 | 编辑补齐（尺码表/属性/包装） | `miaoshou-erp-tiktok-apparel-readiness` + `miaoshou-erp-tiktok-product-edit` | 自动 |
| 6 | 定价 | `mss-vn-pricing` | ✅ 确认 |
| 7 | 发布上架 | `miaoshou-erp-tiktok-product-publish` | ✅ 确认 |
| 8 | 查发布记录验证 | `miaoshou-erp-tiktok-product-publish`（`publish-log`） | 自动 |

## 三个确认点（写操作，必须停下等用户）

1. **认领**：展示「商品标题 / 目标店铺」，等你回复确认后执行 `claim`。
2. **改价**：`mss-vn-pricing` 算出引流品/常规品/利润款三档 VND 售价，等你选定后写回 SKU。
3. **发布**：展示完整商品信息（类目/价格/库存/尺码表/属性），等你回复「确认发布」才提交。

## 每一步的子技能用法

运行时按步加载对应子技能，取其完整说明与脚本；此处只给入口与要点。

### 1. 选品
加载 `tiktok-shop-opportunity-selection`，抓 TikTok 卖家中心「商品机会」数据（高潜力商品/热门关键词/低竞争类目），按潜力分/搜索量/竞争度打分，选出 1 个品。

### 2. 1688 采集
加载 `mss-1688-sourcing`，用第 1 步选出的品去 1688 找货源，采集到妙手公共采集箱，拿到公共箱 `detailId`。

### 3. 认领（确认）
加载 `miaoshou-erp-product-claim`，把公共箱 `detailId` 认领到 TikTok 店铺采集箱。**先展示「商品 + 目标店铺」计划，等确认后再执行**。

### 4. 类目
加载 `miaoshou-erp-tiktok-category-recommend`，匹配 TikTok 叶子类目与必填属性（服装类目常见必填「材质」+ 尺码表）。

### 5. 编辑补齐
服装类目先加载 `miaoshou-erp-tiktok-apparel-readiness`（生成尺码表图并托管 + 填必填材质属性 + 包装尺寸）；再加载 `miaoshou-erp-tiktok-product-edit` 整包保存（回传 ossMd5）。

### 6. 定价（确认）
加载 `mss-vn-pricing`，按采购成本算三档 VND 售价（含平台佣金 16.1%+交易 5%+提现 1%+VAT 10%+达人 10%）。**等你选定档位后**，写回 SKU 的 `price` 与 `priceIncludeVat`（越南站前台取后者，两字段都要改）。

### 7. 发布（确认）
加载 `miaoshou-erp-tiktok-product-publish`，展示发布计划，**等你回复「确认发布」** 后提交 `save_move_collect_task`。

### 8. 验证
`tiktok_publish.py publish-log --item-id <detailId>` 查发布记录；`success` 且有 `platformItemId` 即推送成功（TikTok 端「审核/草稿/已上架」状态需到卖家中心核对）。

## 注意事项

- 写操作（认领/改价/发布）必须逐个人工确认，禁止自动冲到底。
- 每个子技能可能有自己的凭证/登录态要求，缺则停下向用户要，不臆造。
- 服装类目必填尺码表与材质，别漏（见 `miaoshou-erp-tiktok-apparel-readiness`）。
- 越南站前台零售价取 `priceIncludeVat`，改价必须同步该字段（见 `mss-vn-pricing`）。
- 发布是异步提交，`success` ≠ 已上架，第 8 步 + 卖家中心核对才是闭环。
