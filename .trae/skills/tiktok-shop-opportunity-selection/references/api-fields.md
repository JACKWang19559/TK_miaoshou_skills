# TikTok 商品机会数据接口与字段说明

本文档记录 TikTok 卖家中心「商品机会」页面的内部接口与字段，供抓取与选品分析使用。

## 接口清单

域名：`api16-normal-sg.tiktokshopglobalselling.com`（区域会变，如 `-sg`/`-va`）。

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| POST | `/api/v1/product/oc/seller_product_opportunity/seller/lead/list` | **核心：商机线索列表**（分页，每页 100） |
| POST | `/api/v1/product/oc/seller_product_opportunity/shop_filter/get` | 店铺/类目/标签筛选器 |
| POST | `/api/v1/product/oc/seller_product_opportunity/product/performance/Card` | 商品表现卡片 |
| POST | `/api/v1/product/oc/seller_product_opportunity/contract/check` | 提报合同检查 |

## 反爬签名（关键）

所有接口的 query string 都带 `X-Bogus`、`X-Gnarly`、`X-Tts-Oec-Bsid` 签名头，
以及 `msToken` 参数。这些签名由页面 JS（`oec_product_seller_product_opportunity_api.*.js`）
在发请求前动态计算，绑定了 `msToken` 与时间戳。因此：

- **无法离线重放**：脱离浏览器自己算签名极难，直接复制 URL 重放会 403。
- **必须走浏览器上下文**：让页面自己发请求，通过 CDP 监听网络捕获响应体。

## lead/list 响应结构

```json
{
  "code": 0,
  "message": "success",
  "page_number": 1,
  "page_size": 100,
  "total_product_count": 500,
  "data": [ { "lead_id": "...", "lead_name": "...", "...": "..." } ]
}
```

## 筛选参数（实测）

lead/list 的 POST body 通过以下字段控制筛选与分页：

| 字段 | 取值 | 作用 |
| --- | --- | --- |
| `page_number` / `page_size` | 整数 / 100 | 分页，每页 100 条 |
| `category_infos` | `[{"cate_id": 601152, "level": 1}]` | **类目筛选**，cate_id 为类目 ID，level 为级联层级 |
| `tab_code_filter` | `["high_potential_products"]` | 一级 tab「高潜力商品」 |
| `tab_code_filter` | `["high_potential_products","shp_top_products"]` | 二级子筛选「🔥基于市场趋势的热门商品」 |
| `sort_field` | 1 | 排序方式 |
| `use_like` | true/false | 是否「我收藏的」 |

### 类目 ID 获取

类目 ID 即筛选面板级联选择器里 checkbox 的 `value`（如 `601152`=女装与女士内衣）。
常用一级类目 ID 可在打开筛选后，从 `.core-cascader-popup input[type=checkbox]` 的
`value` 读取；也可用 `--list-categories` 逻辑（见 fetch_leads.py）枚举。

### 二级 tab 与 URL 参数

页面二级子筛选会写入 URL query 的 `sub_tabs`：`sub_tabs=shp_top_products` 即
「基于市场趋势的热门商品」。因此抓取时可直接 navigate 到带该参数的 URL，跳过 UI 点击。

## lead 字段说明

| 字段 | 含义 | 对应「商品机会」维度 |
| --- | --- | --- |
| `lead_id` | 商机线索唯一 ID | - |
| `lead_name` | 商机名（常为越南语商品标题/关键词） | 热门关键词 |
| `opportunity_type` | 机会类型（1/2/3，含义待确认） | - |
| `search_volume` | 搜索量 | 热门关键词 / 需求 |
| `online_products` | 在线商品数（越少竞争越小） | 低竞争类目 |
| `l30d_sales_volume` | 近 30 天销量 | 高潜力商品 |
| `l30d_sales_volume_ring_ratio` | 销量环比（%），负值为下滑 | 高潜力商品（趋势） |
| `gmv` / `gmv_l30d` | GMV / 近 30 天 GMV | 高潜力商品 |
| `potential_score` | 平台潜力分 | 高潜力商品 |
| `order` | 订单量 | 高潜力商品 |
| `recommend_price_low` / `recommend_price_high` | 建议价区间 | 定价参考 |
| `curreny` | 币种（如 `₫` 越南盾） | - |
| `level1/2/3_cate_name` | 三级类目名 | 低竞争类目 |
| `level1/2/3_cate_name_key` | 类目 key（如 `magellan_601284`） | - |
| `categories[]` | 类目结构（id/name/level/is_leaf） | - |
| `pic_url[]` / `high_resolution_pic_url` | 商品图 URL | - |
| `sku_names` | SKU 规格名 | - |
| `display_price` | 展示价格文本 | - |
| `is_seller_own` / `is_your_product` | 是否自己店铺的商品 | 提报排除用 |

## 数值格式注意

多数数值字段是**越南语千分位格式的字符串**：用 `.` 作千分位分隔符，例如
`"5.361"` 表示 5361，`"158.015"` 表示 158015，`"0"` 表示 0。
`rank_opportunities.py` 的 `parse_num()` 已按此规则处理（`\d{1,3}(\.\d{3})+` 去点）。
若你抓到的站点是 US/UK 等用 `.` 作小数点的市场，需要改用 `,` 千分位规则，
`parse_num` 中已同时去除逗号，但小数点语义会不同，请自行核对。
