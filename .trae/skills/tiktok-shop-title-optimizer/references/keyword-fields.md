# 热门关键词 tab 接口与字段说明

## 接口参数

热门关键词 tab 复用 `seller/lead/list` 接口，POST body 差异：

| 字段 | 取值 | 作用 |
| --- | --- | --- |
| `opportunity_type` | `2` | 热门关键词 tab（高潜力商品为 `3`） |
| `tab_code_filter` | `["trending_keywords"]` | 热门关键词 tab 过滤 |
| `category_infos` | `[{"cate_id": 601152, "level": 1}]` | 类目筛选（必须，避免无关热搜词） |

URL query 等价参数：`tab=trending_keywords`（可直接 navigate 带该参数）。

## lead 字段（热门关键词特有）

| 字段 | 含义 |
| --- | --- |
| `lead_name` | **关键词**（越南语，含大量无变音拼写） |
| `search_volume` | **搜索量**（越南语千分位，`"3.787"`=3787） |
| `opportunity_type` | `201`=简短搜索词，`202`=长尾词/商品名 |
| `lead_tag[]` | 平台标记：`po_tab_trending_hashtags_new`=TikTok 热门商品，`sc_product_opportunity_filter_condition_feature_option_2`=全球畅销商品 |
| `lead_demands` | 需求标签 |
| `themeList` | 主题列表 |
| `tag_codes` | 标签编码 |

其余字段（`gmv`、`l30d_sales_volume`、`level1/2/3_cate_name`、`pic_url` 等）与高潜力商品一致。

## 关键词数据形态（实测）

`lead_name` 混合三类，优化标题时需区分：

1. **简短搜索词**：`áo cổ lọ`（高领衣）、`áo dây`（吊带）—— 适合融入标题；
2. **店铺名/品牌词**：`gagastore`、`laboutiquevn`、`trami store`、`cotton on vietnam` —— 需过滤；
3. **长商品名**：`Áo Thun Cotton Thiết Kế Dây Treo Ngang Lưng...` —— 需过滤（按词数）。

越南语「无变音拼写」（`a olen` = `áo len`）属于第 1 类，是买家真实搜索方式，
**应保留**，不要当成错词或店铺名误杀。
