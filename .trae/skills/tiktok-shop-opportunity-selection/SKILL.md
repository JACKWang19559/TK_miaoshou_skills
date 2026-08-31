---
name: "tiktok-shop-opportunity-selection"
description: "抓取 TikTok 卖家中心「商品机会」数据并自动选品：注入卖家中心登录 cookie，通过浏览器 CDP 捕获商品机会接口（seller/lead/list，含高潜力商品、热门关键词、低竞争类目字段），按潜力分/搜索量/竞争度打分排序，输出选品清单。Invoke when 用户要爬 TikTok Shop 商品机会数据、用商品机会选品、抓取高潜力商品/热门关键词/低竞争类目，或提到 opportunity/商机/商品机会/选品洞察。"
---

# TikTok 商品机会抓取与选品

把 TikTok 卖家中心自带的「商品机会」数据抓下来，按选品策略打分排序，产出「该选什么品」的清单。商品机会是 TikTok 官方免费的选品工具，包含三块数据：

- **高潜力商品**：`potential_score`、`l30d_sales_volume`（近 30 天销量）、`l30d_sales_volume_ring_ratio`（环比）
- **热门关键词**：`lead_name`、`search_volume`（搜索量）
- **低竞争类目**：`online_products`（在线商品数=竞争度）、三级类目名

## 前提条件（务必先满足）

1. **受管浏览器已启动并开调试端口**：需要一个以 `--remote-debugging-port=9222` 启动的 Chromium 内核浏览器。
   本技能默认端口 9222，可用 `--cdp-port` 覆盖。若使用 bb-browser，它已默认开 9222。
2. **卖家中心登录 cookie 文件**：EditThisCookie 格式的 JSON（含 `cookies` 数组），
   需包含 httpOnly 的 `SELLER_TOKEN`、`UNIFIED_SELLER_TOKEN`、`sessionid` 等。用浏览器
   登录卖家中心后，用 Cookie 导出插件导出即可。
3. **Python 依赖**：`requests`、`websocket-client`（见 `requirements.txt`）。
4. **目标站点有商品机会权限**：部分站点/账号需在卖家中心能正常打开「商品机会」页。

## 工作流

### 第 1 步：注入登录态（可选，单独验证用）

```bash
py scripts/inject_login.py --cookie-file <cookie.json> --region VN
```

执行后浏览器停在商品机会页，人工确认不再跳登录页即为成功。

### 第 2 步：抓取商机数据

```bash
# 基础：抓全部商机（不限类目）
py scripts/fetch_leads.py --cookie-file <cookie.json> --region VN --out opportunity_leads.json

# 推荐：筛选卖家可做的类目 + 「基于市场趋势的热门商品」子筛选
py scripts/fetch_leads.py --cookie-file <cookie.json> --region VN \
    --categories 601152 --subtab trend --out opportunity_leads.json
```

- `--categories`：筛选类目 ID（逗号分隔），如 `601152`=女装与女士内衣。类目 ID 从筛选面板
  级联 checkbox 的 `value` 获取（见 `references/api-fields.md`）。
- `--subtab trend`：切到二级子筛选「🔥基于市场趋势的热门商品」（等价 `sub_tabs=shp_top_products`）。

脚本流程：注入 cookie → 打开商品机会页 →（可选）筛选类目 + 切子 tab → 监听网络捕获
`seller/lead/list` 响应 → 滚动翻页收集商机 → 按 `lead_id` 去重落盘 JSON。
**顺序保证：先完成筛选，再滚动翻页**，避免抓到未筛选的数据。

### 第 3 步：打分排序选品

```bash
py scripts/rank_opportunities.py --input opportunity_leads.json --strategy balanced --top 20
```

`--strategy` 四选一：
- `hot`：追爆款（销量 + 需求为主）
- `rising`：起量（销量环比增长为主）
- `blue_ocean`：蓝海（低竞争 + 需求）
- `balanced`：均衡（默认）

## 安全规则（必须遵守）

- **凭证绝不落库**：cookie 文件只读入内存并写入浏览器，绝不打印 cookie 值、绝不写进任何 git 仓库。
  把 cookie 文件路径加入 `.gitignore`（或放在仓库外）。
- **只读、低频**：本技能只读商机数据，不做提报/修改；避免高频轮询，防止触发风控。
- **不打印签名头**：脚本不输出 `X-Bogus`/`X-Gnarly`/`msToken` 等，避免泄露会话信息。

## 避坑

- 接口带 `X-Bogus`/`X-Gnarly` 签名，**不能离线直连**，必须走浏览器上下文（见 `references/api-fields.md`）。
- 越南语数值用 `.` 作千分位（`"5.361"` = 5361），`parse_num` 已处理；US/UK 站点语义不同需自校。
- 抓取前确保 cookie 未过期（`SELLER_TOKEN` 等 JWT 的 `exp` 较短），过期会重定向回登录页。
- `fetch_leads.py` 依赖滚动触发分页；若页面是「点击加载更多」而非无限滚动，需微调触发方式。
