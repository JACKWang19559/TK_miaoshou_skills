---
name: "mss-1688-sourcing"
description: "妙手ERP经API从1688选品采集到公共采集箱的完整工作流：选品定位（引流品/季节品/爆款延伸/长青品）、1688货源链接获取、预览校验、fetch_item批量采集、采集结果核验与detailId交接。当用户需要在妙手中采集1688商品、把1688链接导入妙手、批量采集货源、或提到妙手选品/1688采集/fetch_item时调用。货叮咚浏览器铺货的对应方案见 hdd-1688-sourcing。"
---

# 妙手 1688 选品采集（API 版）

在妙手 ERP 轨道上，把 1688（及 AliExpress/淘宝/天猫/拼多多等）货源商品链接通过开放平台 API 采集进妙手「公共采集箱」，返回采集箱详情 ID（detailId）供后续认领到 TikTok 店铺。

与货叮咚轨道的区别：货叮咚 `hdd-1688-sourcing` 是在货叮咚内嵌 1688 页面里**浏览器点击铺货**；本技能是**纯 API 收链接**——先拿到 1688 商品详情链接，再调用 `fetch_item` 接口采集。API 方式更稳定、可批量、无跨域 iframe 问题，但**不负责在 1688 站内搜索浏览**，找品环节需另行获取链接（见第 2 步）。

## 底层能力

本技能是编排层，实际 API 调用由妙手官方原子技能 `miaoshou-erp-source-import` 完成：

- 接口：`POST /open/v1/product/common_collect_box/common_collect_box/fetch_item`
- 请求字段：`collectLinks`（货源链接数组）
- 返回字段：`data.sourceItemIdAndDetailIdMap`（货源ID → 采集箱详情ID 的映射）
- 脚本：`miaoshou-erp-source-import/scripts/source_collect.py`（标准入口，支持 `--urls` 多链接）

## 前置条件

1. **妙手开放平台凭证已配置**：`miaoshou-erp-source-import/resources/config.json` 中 `app_key` / `app_secret` 已填（或设置环境变量 `MIAOSHOU_APP_KEY` / `MIAOSHOU_APP_SECRET`）。
2. **Python 依赖**：仅需 `requests`（`pip install requests`）。所有 Python 命令用 `py` 开头。
3. **店铺授权有效**：用 `miaoshou-erp-shop-query` 确认目标 TikTok 店铺授权未过期（授权到期后采集本身不受影响，但后续认领会失败）。
4. **先做只读自检**（不提交商品）：
   ```powershell
   py "<skills根目录>/miaoshou-erp-source-import/scripts/check_config.py"
   ```
   `has_app_key` / `has_app_secret` 为 true 即可。本接口用 app 凭证签名鉴权，**无需 x-account-id / cookie**。

> 路径说明：`<skills根目录>` 在 Trae Work 为工作区 `.trae/skills/`，在 Claude Code 为用户级 `~/.claude/skills/`（Windows: `C:\Users\<用户>\.claude\skills\`）。下文所有 `py "<...>/..."` 命令均按此定位妙手原子技能脚本。

## 操作流程

### 第 1 步：选品定位与关键词决策

采集前先明确这批货的选品定位，决定找什么品、用什么关键词（与货叮咚轨道同一套选品方法论）：

| 选品类型 | 适用场景 | 选品特征 | 关键词倾向 |
|---|---|---|---|
| 引流品 | 新账号起号 | 低价、基础款、应季、一件起订、低利润 | 品类词 + 价格敏感属性（低价/批发/清仓） |
| 季节品 | 当季冲量 | 强季节属性、上新快 | 品类词 + 当季属性（夏季=透气/薄款/防晒） |
| 爆款延伸品 | 跟卖放量 | 已验证爆款的相似/配套款 | 爆款词 + 款式变体 |
| 长青品 | 稳定动销 | 全年可卖、退货低、刚需 | 品类词 + 经典/基础/百搭 |

目标市场为越南时，结合越南气候（常年高温、雨季）与 TikTok 越南站偏好决策品类。

### 第 2 步：获取 1688 商品详情链接

妙手 API 只收「商品详情页链接」，不收搜索页/分类页/店铺页。链接来源两种模式：

- **模式 A（用户/选品流程提供）**：用户直接给出一个或多个 1688 商品链接，或由跨境选品技能（`crossborder-ecommerce-product-selection`）调研后产出候选链接。这是 API 工作流最常见的入口。
- **模式 B（浏览器找品）**：用 agent-browser 打开 1688（`https://www.1688.com` 或 `https://detail.1688.com`），按第 1 步关键词搜索、筛选（价格/销量/一件起订/回头率/发货时效），逐个进入商品详情页，复制详情链接。agent-browser 环境准备见 `hdd-1688-sourcing` 技能「环境准备」章节。

**合法链接格式**（脚本会做格式校验）：
- 1688：`https://detail.1688.com/offer/{offerId}.html`（offerId 即货源ID，如 `1052211637322`）
- AliExpress：`https://www.aliexpress.com/item/{id}.html`
- 淘宝：`https://item.taobao.com/item.htm?id={id}`；天猫：`https://detail.tmall.com/item.htm?id={id}`
- 拼多多：`https://mobile.yangkeduo.com/product.html?goods_id={id}`

链接可带 `spm` 等跟踪参数，脚本不会因此拒绝；但搜索页、分类页、店铺首页、短链需先澄清或转成详情链接。

### 第 3 步：预览校验（只读，不提交）

提交前先预览，确认链接数量、来源域名、去重结果：

```powershell
py "<skills根目录>/miaoshou-erp-source-import/scripts/source_collect.py" --urls "https://detail.1688.com/offer/1052211637322.html"
```

不带 `--confirm` 时只预览不采集，输出示例：
```
采集计划预览
- 可提交链接数: 1
- 来源域名: detail.1688.com
```

多个链接依次跟在 `--urls` 后（空格分隔）。若含非法链接，脚本会区分有效/无效；默认不提交，需用户决定「修正」或「跳过」（跳过时才加 `--ignore-invalid`）。

### 第 4 步：确认后提交采集

采集是**写操作**（会在公共采集箱创建商品记录），必须先向用户出示采集计划并获明确确认：

```text
请确认采集计划：
- 链接数量：N
- 来源域名：detail.1688.com, ...
- 目标位置：妙手ERP公共采集箱
- 不会执行：编辑、认领、发布
确认后才会提交。请回复"确认采集"或"取消"。
```

确认后提交（加 `--confirm`，`--json` 便于程序解析）：

```powershell
py "<skills根目录>/miaoshou-erp-source-import/scripts/source_collect.py" --urls "<链接1>" "<链接2>" --confirm --json
```

成功响应（实测）：
```json
{
  "submitted_count": 1,
  "api_response": {
    "result": "success",
    "code": "success",
    "data": {
      "sourceItemIdAndDetailIdMap": {
        "1052211637322": 3949403282
      }
    }
  }
}
```

**务必记录映射关系**：键是货源ID（1688 offerId），值是妙手公共采集箱详情 ID（detailId）。后续认领、编辑、出单后 1688 同款代发都要用到这两个 ID。

### 第 5 步：等待异步抓取并核验

妙手后台收到链接后**异步抓取**商品数据（标题、价格、SKU、图片等），不是立即完成。提交后等待约 **8-10 秒**，再查公共采集箱确认：

```powershell
py "<skills根目录>/miaoshou-erp-common-collectbox-manage/scripts/collectbox_crud.py" list --status all --page 1 --size 20
```

核验要点：
- 新商品出现在列表，`状态: success`（若为 `collectFail` 说明货源下架/需登录/抓取异常，换同款货源重新采集）。
- 标题、采集价（CNY）、库存、来源（1688 + 货源ID）与预期一致。
- 也可用 `list --status collectFail` 单独排查失败项。

### 第 6 步：交接下游

采集成功后，把 detailId 交给下游技能：
- 认领 TikTok：`miaoshou-erp-product-claim`（公共采集箱 → TikTok 平台采集箱）
- 采集箱内编辑（改价/库存/重量等）：`miaoshou-erp-common-collectbox-manage`
- 认领后 TK 侧编辑（标题/属性/SKU/图片/物流）：`miaoshou-erp-tiktok-product-edit`

## 批量采集

`--urls` 接受多个链接（空格分隔），一次 `fetch_item` 调用可批量提交：

```powershell
py "<skills根目录>/miaoshou-erp-source-import/scripts/source_collect.py" --urls "https://detail.1688.com/offer/A.html" "https://detail.1688.com/offer/B.html" "https://detail.1688.com/offer/C.html" --confirm --json
```

- 响应 `sourceItemIdAndDetailIdMap` 会包含每个成功链接的映射。
- 部分成功时，分别报告成功映射与失败链接，不要把失败项当作成功。
- 去重：脚本会自动对重复链接去重（保留原顺序）；同一货源重复采集可能在采集箱产生重复记录，提交前先去重。

也可用 `source_import.py preview --input links.txt --json` 从文件读取链接做预览，适合大批量。

## 关键踩坑

1. **API 不负责找品**：`fetch_item` 只收现成的商品详情链接。不要指望它搜索 1688；找品走模式 A/B。
2. **必须是详情页链接**：搜索页、分类页、店铺页、短链会被校验拦截或导致抓取失败。1688 链接认 `/offer/{id}.html` 或带 `offerId`/`offerid` 参数的详情 URL。
3. **采集是异步的**：提交成功只代表「妙手已受理」，商品数据约 8-10 秒后才落库。立即查列表可能查不到，需等待后核验；状态以 `success` / `collectFail` 为准。
4. **写操作要确认**：采集会在采集箱建记录，批量提交前必须出示链接数 + 域名并获用户确认。
5. **留好 ID 映射**：`sourceItemIdAndDetailIdMap` 的货源ID 和 detailId 是后续全链路（认领/编辑/代发）的关键，务必落表记录，不要只看"成功"就过。
6. **采集失败处理**：`collectFail` 多因 1688 货源下架、需登录、或链接已失效；回 1688 换同款有效货源重新采集，不要反复重试同一坏链。
7. **库存规范后置**：采集进来的商品库存是 1688 原始库存（可能上万），统一改为 555 是在「采集箱编辑 / TK 编辑」环节做，不在本技能处理。
8. **凭证安全**：app_secret 只存在本地 config.json 或环境变量，绝不打印签名头、不把 config.json 提交 git（已被 .gitignore 保护）。

## 完成标准

- 目标 1688 商品在妙手公共采集箱可见，状态 `success`
- 记录每个商品的「货源ID（1688 offerId）↔ 妙手 detailId」映射
- 下一步交给 `miaoshou-erp-product-claim` 认领到 TikTok 越南店
