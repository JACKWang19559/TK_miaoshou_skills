---
name: "tiktok-shop-title-optimizer"
description: "抓 TikTok 卖家中心「商品机会→热门关键词」tab 的热搜词，用于优化产品标题，让标题关联上热搜关键词。复用 tiktok-shop-opportunity-selection 的 fetch_leads.py（--tab trending_keywords）抓关键词，再用 optimize_title.py 经五级过滤（三级类目→品牌/店铺名→词数/搜索量→属性冲突→标题核心词相关性）后按 相关性>搜索量 排序，给出标题融入建议。Invoke when 用户要找 TikTok 热搜关键词、用热搜词优化产品标题、提升标题搜索命中率，或提到 热门关键词/trending keywords/标题优化/关键词关联。"
---

# TikTok 热搜关键词标题优化

抓「商品机会 → 热门关键词」tab 的**热搜词**，用来优化产品标题，让标题关联上买家真实搜索的关键词，提升搜索命中率。

## 前提条件

与本技能库 `tiktok-shop-opportunity-selection` 相同：
1. 受管浏览器以 `--remote-debugging-port=9222` 启动；
2. 卖家中心登录 cookie 文件（EditThisCookie 格式）；
3. Python 依赖 `requests`、`websocket-client`（抓取用）；`optimize_title.py` 只用标准库。

## 工作流

### 第 1 步：抓热门关键词（必须筛选类目）

```bash
py <tiktok-shop-opportunity-selection>/scripts/fetch_leads.py \
    --cookie-file <cookie.json> --region VN \
    --tab trending_keywords --categories 601152 \
    --lead-source UNMET_DEMAND \
    --out keyword_leads.json
```

- `--tab trending_keywords` 切到「热门关键词」tab（等价 URL `tab=trending_keywords`，POST 参数
  `opportunity_type=2`、`tab_code_filter=["trending_keywords"]`）。
- `--categories` 必须筛选类目（如 `601152`=女装与女士内衣），避免抓到无关类目的热搜词。
- `--lead-source UNMET_DEMAND` 可选，只抓「未满足需求」线索（UI 勾选，见 opportunity-selection 文档）。

### 第 2 步：用热搜词优化标题

```bash
# 推荐：指定产品三级类目 ID（从关键词数据的 level3_cate_name_key 取，如 magellan_601284）
py optimize_title.py --keywords keyword_leads.json \
    --title "Áo khoác len nữ dáng dài cổ V" \
    --cate-id 601284 --top 6

# 或不传类目，靠标题相关性自动跨类目匹配（越南语去变音后核心词交集）
py optimize_title.py --keywords keyword_leads.json \
    --title "Áo sơ mi nữ công sở tay dài" --top 6
```

输出：各阶段过滤统计 → 候选热搜词榜单（`[搜索量|rel=重合词数]`，按 **相关性 > 搜索量** 排序）
→ 融入后的标题 + 已融入的词。

参数说明：
- `--cate-id`：三级类目 ID（如 `601284`=女士毛衣与针织衫），按 `level3_cate_name_key` 硬过滤，**推荐**；
- `--category`：类目名子串（如 `女士毛衣与针织衫`），与 `--cate-id` 二选一；
- `--top`：最多融入的热搜词数，默认 5；
- `--max-words`：关键词最大词数（过滤长商品名），默认 6；
- `--max-len`：标题最大长度，默认 200；
- `--min-volume`：最小搜索量阈值，默认 1；
- `--no-relevance`：关闭标题相关性 / 属性冲突过滤（默认开启，调试用）。

## 过滤管线（optimize_title.py 内部）

热搜词数据较「脏」，融入前必须过五级过滤，并打印每级淘汰数量：

1. **三级类目过滤**：`--cate-id` / `--category` 硬过滤，只留产品所属类目；
2. **品牌 / 店铺名过滤**：含 `store/shop/official/clothing/wear/fashion` 等标志 token、
   无空格纯 ASCII 单串（`laboutiquevn`）、或纯 ASCII 且含非时尚白名单词的生造词
   （`long ecochic`、`lumi wear`、`sushi clothing`）；
3. **词数 / 搜索量过滤**：去掉长商品名（>`--max-words` 词）与低搜索量词；
4. **属性冲突过滤**（越南语服饰）：归一化去变音后子串匹配，如标题含 `cổ V`（V 领）
   则剔除 `cổ lọ/tròn/trụ`（高领/圆领/立领）词；标题 `tay dài`（长袖）剔除
   `cộc tay/ngắn tay`（短袖）词，反向同理；
5. **标题相关性过滤**：标题去变音分词、去掉 `nữ/áo/dáng` 等泛词得到核心词集合，
   关键词核心词与之交集为 0 即剔除（如衬衫词不会堆到外套标题）；交集个数记为
   `rel` 得分，融入排序时 rel 优先于搜索量。

融入时还会自动去重（与原标题 / 已加词重复或互为子串的跳过）。

## 避坑（重要）

- **自动结果仍需人工确认**：过滤能挡住跨类目、品牌词和明显属性冲突，但同类目内
  材质 / 风格差异（如 `len lông vũ` 羽毛纱、`nhung gân tăm` 丝绒）仍需人工判断是否匹配产品。
- **无变音拼写是有效热搜词**：越南买家常不打变音符号搜索，`a olen`、`aokhoaclen` 这类词
  正是要融入标题的，白名单已覆盖 `ao/len/khoac/quan/ren/thun` 等核心词，不会被误杀。
- **类目字段可能错配**：`level3_cate_name` 偶有错配，建议优先传 `--cate-id` 并扫一眼候选清单。
- **候选过少时**：说明该三级类目 + 未满足需求的词池本来就小，可去掉 `--cate-id`
  靠相关性跨类目捞词，或放宽 `--max-words`；不要为凑数加 `--no-relevance`。

## 安全规则

- cookie 文件只读内存、不入库、不打印；本 skill 只读商机数据，不做提报/修改。
