---
name: "tiktok-shop-title-optimizer"
description: "抓 TikTok 卖家中心「商品机会→热门关键词」tab 的热搜词，用于优化产品标题，让标题关联上热搜关键词。复用 tiktok-shop-opportunity-selection 的 fetch_leads.py（--tab trending_keywords）抓关键词，再用 optimize_title.py 经五级过滤（三级类目→品牌/店铺名→词数/搜索量→属性冲突→标题核心词相关性）后按 相关性>搜索量 排序给出标题；apply_title.py 可把优化后的标题只改 title 字段写回妙手采集箱。Invoke when 用户要找 TikTok 热搜关键词、用热搜词优化产品标题、把优化标题写回妙手、提升标题搜索命中率，或提到 热门关键词/trending keywords/标题优化/关键词关联。"
---

# TikTok 热搜关键词标题优化

抓「商品机会 → 热门关键词」tab 的**热搜词**，用来优化产品标题，让标题关联上买家真实搜索的关键词，提升搜索命中率。

## 前提条件

与本技能库 `tiktok-shop-opportunity-selection` 相同：
1. 受管浏览器以 `--remote-debugging-port=9222` 启动；
2. 卖家中心登录 cookie 文件（EditThisCookie 格式）；
3. Python 依赖 `requests`、`websocket-client`（抓取用）；`optimize_title.py`、`apply_title.py` 只用标准库。

`apply_title.py` 写回妙手时，还需复用 `miaoshou-erp-tiktok-product-edit` 的凭证：
4. 妙手开放平台 `AppKey`/`AppSecret` 已配置（`miaoshou-erp-tiktok-product-edit/resources/config.json`
   或环境变量 `MIAOSHOU_APP_KEY`/`MIAOSHOU_APP_SECRET`）；IP 在白名单内。

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

### 第 3 步：把优化后的标题写回妙手采集箱（apply_title.py）

`apply_title.py` 打通「查商品 → 取类目 → 优化标题 → 预览 → 写回 → 复查」全闭环。
它复用 `miaoshou-erp-tiktok-product-edit` 的 `tiktok_collectbox.py` 做查询与保存，自动定位脚本，
只改 `title` 一个字段，其余价格/库存/图片/属性/SKU 原样保留。

```bash
# 预览（默认 dry-run，绝不写）
py apply_title.py --detail-id <detailId> --keywords keyword_leads.json \
    --mode site --site VN

# 确认无误后写回（--execute + 对话层人工确认双门）
py apply_title.py --detail-id <detailId> --keywords keyword_leads.json \
    --mode site --site VN --execute

# 店铺模式
py apply_title.py --detail-id <detailId> --keywords keyword_leads.json \
    --mode shop --shop-id <shopId> --execute
```

参数说明：
- `--detail-id`：采集箱详情 ID（必填）；
- `--mode`：`site`（站点模式，默认）或 `shop`（店铺模式）；site 模式必传 `--site`，
  shop 模式必传 `--shop-id`；
- `--keywords`：热搜词 JSON（必填）；
- `--cate-id`：可选，覆盖自动提取的类目 ID（默认从详情 `cid` 字段提取）；
- `--top` / `--max-words` / `--max-len` / `--min-volume`：与 `optimize_title.py` 同义，
  `--max-len` 默认 255（TikTok 标题上限）；
- `--execute`：执行写回；不传则只预览；
- `--collectbox-script`：可选，覆盖 `tiktok_collectbox.py` 路径（默认自动定位同级妙手技能）。

写回安全规则：候选词为 0、标题超长、或新旧标题一致时中止不写；写回后自动重新拉详情
复查标题是否已更新。

**标题语言自动切换**：标题语言取决于卖家手动填写——跨境商品采集进来是中文源标题，
妙手/TikTok **不会自动翻译**，需卖家手动把标题翻译成目标站点语言（如越南语）。
`apply_title.py` 按实际读到的标题语言自动选择过滤策略：
- 读到**越南语标题**（卖家已手动翻译）→ 走完整五级过滤（含越南语相关性、属性冲突）；
- 读到**中文标题**（尚未翻译）→ 跳过越南语相关性 / 属性冲突过滤，改用**服饰信号词**兜底
  （要求候选词含 `áo/quần/váy/len/thun/...` 等服饰核心词，挡住类目错配混入的羽毛球/拖鞋/手表等非服饰词）。

**必填字段兜底**：`deliveryOptionSetType`（发货方式，标准值 `default`）是 save 必填字段，
采集/认领后可能缺失导致写回报「deliveryOptionSetType 必填」。`apply_title.py` 写回前检测到
缺失会自动补 `default`。

## 过滤管线（optimize_title.py 内部）

热搜词数据较「脏」，融入前必须过五级过滤，并打印每级淘汰数量：

1. **三级类目过滤**：`--cate-id` / `--category` 硬过滤，只留产品所属类目；
2. **品牌 / 店铺名过滤**：含 `store/shop/official/clothing/wear/fashion` 等标志 token、
   无空格纯 ASCII 单串（`laboutiquevn`）、或纯 ASCII 且含非时尚白名单词的生造词
   （`long ecochic`、`lumi wear`、`sushi clothing`）；
3. **词数 / 搜索量过滤**：去掉长商品名（>`--max-words` 词）与低搜索量词；
   （中文标题场景额外要求候选词含服饰信号词，见上文「标题语言自动切换」）
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

- cookie 文件只读内存、不入库、不打印；抓词阶段只读商机数据，不做提报/修改。
- 写回妙手为高影响写操作：`apply_title.py` 默认 dry-run，仅加 `--execute` 且对话层人工确认后才写，
  且只改 `title` 字段、整包深拷贝保留其余字段，避免抹掉价格/库存/图片/规格。
- 写回失败（ossMd5Mismatch 等）应重新拉详情再试，不强行重试。
