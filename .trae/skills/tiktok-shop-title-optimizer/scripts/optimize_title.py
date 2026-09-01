# -*- coding: utf-8 -*-
"""用热门关键词优化产品标题，让标题关联上同类目的热搜词。

输入：
- 关键词 JSON：由 fetch_leads.py --tab trending_keywords 抓取
  （含 lead_name、search_volume、level3_cate_name(_key) 等）。
- 产品标题：命令行传入。

过滤管线（层层收紧，避免不相关词 / 品牌词污染标题）：
1. 三级类目过滤（--cate-id / --category）：只保留产品所属类目的热搜词；
2. 店铺 / 品牌名过滤：含 store/shop/clothing/wear 等品牌后缀，
   或纯 ASCII 且不含时尚白名单词的生造词（如 long ecochic、lumi wear）；
3. 词数 / 搜索量过滤：去掉长商品名与低搜索量词；
4. 标题相关性过滤（默认开启）：越南语去变音后分词，与标题核心词
   （去掉 nữ/áo 等泛词）至少有一个交集，防止把「衬衫」词堆到「外套」标题里。

用法：
    py optimize_title.py --keywords keyword_leads.json \
        --title "Áo khoác len nữ dáng dài cổ V" \
        --cate-id 601284 --top 6
"""
import argparse
import json
import re
import unicodedata

# 越南语千分位格式：1.234 / 12.345（用 . 作千分位分隔符）
_THOUSANDS_RE = re.compile(r"-?\d{1,3}(\.\d{3})+")

# 类目 key 中的数字 ID，如 magellan_601284 → 601284
_CATE_ID_RE = re.compile(r"(\d+)")

# 品牌 / 店铺名标志词（作为独立 token 出现即判定为品牌词）
BRAND_MARKERS = {
    "store", "shop", "shops", "official", "boutique", "clothing",
    "fashion", "wear", "studio", "collection",
}

# 纯 ASCII 热搜词的白名单：只有每个实义词都在表内才允许通过，
# 否则视为生造品牌名（long ecochic / lumi wear / sushi clothing 这类）。
ASCII_FASHION_WHITELIST = {
    # 英文服饰词
    "sweater", "cardigan", "knit", "knitted", "wool", "coat", "jacket",
    "blazer", "hoodie", "tee", "shirt", "top", "tops", "dress", "skirt",
    "pants", "pant", "jeans", "jean", "shorts", "short", "crop", "croptop",
    "tank", "cami", "camisole", "vest", "polo", "sleeve", "sleeveless",
    "body", "bodysuit", "cotton", "lace", "silk", "denim", "leather",
    "long", "bigsize", "oversize", "oversized", "size", "basic", "vintage",
    "sexy", "slim", "loose", "wide", "set", "baby", "doll", "babydoll",
    # 越南语无变音核心词（去变音后也长这样）
    "ao", "len", "khoac", "quan", "vai", "soc", "ren", "thun", "mi",
    "so", "co", "tay", "dai", "ngan", "khoe", "body", "bigsize", "form",
}

# 标题相关性匹配时的泛化停用词（不代表品类相关性）
TITLE_STOPWORDS = {
    "nu", "ao", "cai", "chiec", "cho", "dang", "dep", "gia", "re", "hot",
    "nhat", "loai", "kieu", "mau", "size", "bigsize", "freesize", "form",
    "2025", "2026", "2024", "new", "sale", "free", "ship", "v", "x",
}

# 越南语服饰属性矛盾对（归一化后子串匹配）：
# 标题命中任一片语且关键词命中同组任一片语 → 属性冲突，剔除。
# 例如标题「cổ V」（V 领）不能配「áo cổ lọ」（高领）。
CONTRADICTION_GROUPS = [
    # 领型：V 领 vs 高领/圆领/立领/心形领/U 领
    (["co v"], ["co lo", "co tron", "co tru", "co tim", "co duc", "co u"]),
    (["co lo", "co tron", "co tru", "co tim"], ["co v"]),
    # 袖长：长袖 vs 短袖
    (["tay dai", "dai tay"], ["coc tay", "tay ngan", "ngan tay"]),
    (["coc tay", "tay ngan", "ngan tay"], ["tay dai", "dai tay"]),
]

# 服饰信号词（去变音后 token）。中文标题无法与越南语热搜词做词面相关性，
# 改为要求关键词含至少一个服饰核心词，挡住类目错配混入的
# 羽毛球（cầu lông/vợt）、拖鞋（dép/đế trấu）、手表（đồng hồ）等非服饰词。
APPAREL_SIGNALS = {
    # 越南语服饰核心词（去变音后）
    "ao", "quan", "vay", "dam", "len", "thun", "ren", "khoac",
    "bigsize", "baby", "dang", "juyp",
    # 英语服饰核心词
    "shirt", "tee", "top", "tops", "dress", "skirt", "pants", "jeans",
    "sweater", "cardigan", "knit", "blazer", "hoodie", "polo",
    "bodysuit", "crop", "tank",
}


def parse_num(value):
    """把越南语千分位格式的数值字符串解析为 float。

    Args:
        value: 字符串或数值，可能为 None / 空串。

    Returns:
        解析后的浮点数；无法解析时返回 0.0。
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in ("-", "—", "N/A", "null"):
        return 0.0
    if _THOUSANDS_RE.fullmatch(text):
        text = text.replace(".", "")
    text = text.replace(",", "").replace("₫", "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def load_keywords(path):
    """读取关键词 JSON，返回关键词列表（dict 列表）。

    Args:
        path: fetch_leads.py 输出的 JSON 文件路径。

    Returns:
        leads 数组（或空列表）。
    """
    with open(path, encoding="utf-8-sig") as fh:
        raw = json.load(fh)
    return raw.get("leads", [])


def normalize_vi(text):
    """越南语 / 英文文本归一化：小写、去变音符号、只保留 a-z0-9 与空格。

    例：``Áo khoác len Nữ`` → ``ao khoac len nu``。

    Args:
        text: 原始文本。

    Returns:
        归一化后的字符串。
    """
    text = text.lower().replace("đ", "d").replace("Đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def core_tokens(text):
    """提取标题 / 关键词的核心词（去变音、去停用词、去单字符）。

    Args:
        text: 原始越南语 / 英文文本。

    Returns:
        核心词集合（小写、无变音）。
    """
    tokens = normalize_vi(text).split()
    return {t for t in tokens if len(t) >= 2 and t not in TITLE_STOPWORDS}


def is_cjk_title(text):
    """判断标题是否以中日韩等非拉丁脚本为主（如中文标题）。

    中文标题经 normalize_vi 后中文字符会被清空，无法与越南语热搜词做
    词面交集，相关性过滤会误杀全部词。此时应跳过相关性 / 属性冲突过滤，
    只靠类目过滤保证相关性（跨境「中文标题 + 追加越南语热搜词」场景）。

    Args:
        text: 标题文本。

    Returns:
        中文字符数大于 0 且不少于拉丁字母数时返回 True。
    """
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    return cjk > 0 and cjk >= latin


def is_shop_name(name):
    """判断关键词是否为店铺名 / 品牌名。

    规则：
    1. 含 store/shop/official/clothing/wear 等品牌标志 token；
    2. 无空格且纯 ASCII 的单串（如 laboutiquevn、gagastore）；
    3. 纯 ASCII 短语中存在不在时尚白名单里的实义词（如 long ecochic、
       lumi wear、sushi clothing），视为生造品牌名。
    越南语「无变音拼写」热搜词通常含 ao/len/khoac 等白名单词，不受规则 3 误杀。

    Args:
        name: 关键词文本。

    Returns:
        若判断为店铺 / 品牌名返回 True。
    """
    name_lower = name.lower()
    tokens = name_lower.split()
    # 规则 1：品牌标志 token
    if any(tok in BRAND_MARKERS for tok in tokens):
        return True
    # 规则 2：纯 ASCII 单串
    if " " not in name_lower and name.isascii():
        return True
    # 规则 3：纯 ASCII 短语，实义词必须全部命中白名单
    if name.isascii():
        content_tokens = [t for t in tokens if len(t) >= 2]
        if content_tokens and any(
            t not in ASCII_FASHION_WHITELIST for t in content_tokens
        ):
            return True
    # 规则 4：纯 ASCII 短语含单字符字母 token（如 ``knit e``），视为噪音词
    if name.isascii() and any(len(t) == 1 and t.isalpha() for t in tokens):
        return True
    return False


def extract_cate_id(lead):
    """从 lead 的 level3_cate_name_key（如 magellan_601284）提取三级类目 ID。

    Args:
        lead: 单条关键词 dict。

    Returns:
        类目 ID 字符串（如 ``601284``），取不到返回 None。
    """
    key = lead.get("level3_cate_name_key") or ""
    match = _CATE_ID_RE.search(key)
    return match.group(1) if match else None


def relevance_score(name, title_core):
    """关键词与标题的相关性得分（核心词交集个数，0 表示不相关）。

    Args:
        name: 关键词文本。
        title_core: 标题核心词集合。

    Returns:
        交集核心词数量。
    """
    if not title_core:
        return 1
    return len(core_tokens(name) & title_core)


def is_contradictory(name, title_norm):
    """判断关键词与标题是否存在服饰属性冲突（领型 / 袖长）。

    Args:
        name: 关键词文本。
        title_norm: 归一化后的标题（normalize_vi 输出）。

    Returns:
        存在属性冲突返回 True。
    """
    kw_norm = normalize_vi(name)
    for title_pats, kw_pats in CONTRADICTION_GROUPS:
        if any(p in title_norm for p in title_pats) and \
                any(p in kw_norm for p in kw_pats):
            return True
    return False


def filter_keywords(leads, cate_id=None, category=None, max_words=8,
                    min_volume=1, title_core=None, title_norm=None,
                    require_apparel_signal=False):
    """过滤关键词：三级类目 → 品牌词 → 服饰信号 → 词数/搜索量 → 属性冲突 → 相关性。

    Args:
        leads: 关键词原始列表。
        cate_id: 可选，三级类目 ID（如 ``601284``），按 level3_cate_name_key 过滤。
        category: 可选，类目名子串（如 ``女士毛衣与针织衫``），按类目路径过滤。
        max_words: 最大词数，过滤掉长商品名，保留简短搜索词。
        min_volume: 最小搜索量阈值。
        title_core: 可选，标题核心词集合；传入时启用相关性过滤与打分。
        title_norm: 可选，归一化标题；传入时启用属性冲突过滤。
        require_apparel_signal: 可选，要求关键词含服饰信号词（中文标题场景兜底）。

    Returns:
        (keywords, stats)：
        - keywords: [{name, volume, category, cate_id, rel}] 列表，rel 为
          与标题的核心词重合数（越大越相关）；
        - stats: 各阶段淘汰数量统计。
    """
    stats = {"total": len(leads), "cate": 0, "brand": 0, "non_apparel": 0,
             "words": 0, "volume": 0, "contradiction": 0, "relevance": 0}
    result = []
    for lead in leads:
        name = (lead.get("lead_name") or "").strip()
        if not name:
            continue
        lead_cate_id = extract_cate_id(lead)
        cate_path = "/".join(filter(None, [
            lead.get("level1_cate_name"),
            lead.get("level2_cate_name"),
            lead.get("level3_cate_name"),
        ]))
        # 1. 三级类目过滤
        if cate_id and lead_cate_id != str(cate_id):
            stats["cate"] += 1
            continue
        if category and category not in cate_path:
            stats["cate"] += 1
            continue
        # 2. 店铺 / 品牌名过滤
        if is_shop_name(name):
            stats["brand"] += 1
            continue
        # 2.5 服饰信号词过滤（中文标题场景：挡类目错配的非服饰词）
        if require_apparel_signal and not (core_tokens(name) & APPAREL_SIGNALS):
            stats["non_apparel"] += 1
            continue
        # 3. 词数过滤：热搜词应是简短搜索词，而非长商品名
        if len(name.split()) > max_words:
            stats["words"] += 1
            continue
        volume = parse_num(lead.get("search_volume"))
        if volume < min_volume:
            stats["volume"] += 1
            continue
        # 4. 属性冲突过滤（如 V 领标题配高领词）
        if title_norm is not None and is_contradictory(name, title_norm):
            stats["contradiction"] += 1
            continue
        # 5. 标题相关性过滤 + 重合词数打分
        rel = relevance_score(name, title_core) if title_core is not None else 1
        if title_core is not None and rel == 0:
            stats["relevance"] += 1
            continue
        result.append({
            "name": name,
            "volume": volume,
            "category": cate_path,
            "cate_id": lead_cate_id,
            "rel": rel,
        })
    return result, stats


def optimize_title(keywords, title, top=5, max_len=200):
    """把热搜词融入产品标题（追加式，自动去重与冗余包含）。

    Args:
        keywords: filter_keywords 的过滤结果。
        title: 原始产品标题。
        top: 最多融入的关键词数。
        max_len: 标题最大长度（TikTok 标题有长度限制）。

    Returns:
        (new_title, added) 优化后的标题与已融入的关键词列表。
    """
    # 排序：相关性重合词数优先，其次搜索量
    ranked = sorted(keywords, key=lambda k: (-k.get("rel", 1), -k["volume"]))
    added = []
    added_lower = []
    new_title = title
    title_lower = title.lower()

    for kw in ranked:
        if len(added) >= top:
            break
        name = kw["name"]
        name_lower = name.lower()
        # 与原标题或已加词重复
        if name_lower in title_lower or name_lower in added_lower:
            continue
        # 与已加词互为子串 → 冗余，跳过
        if any(a in name_lower or name_lower in a for a in added_lower):
            continue
        if len(new_title) + len(name) + 1 > max_len:
            continue
        added.append(name)
        added_lower.append(name_lower)
        new_title += " " + name

    return new_title, added


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="用热门关键词优化产品标题")
    parser.add_argument("--keywords", required=True,
                        help="fetch_leads.py 抓取的关键词 JSON")
    parser.add_argument("--title", required=True, help="原始产品标题")
    parser.add_argument("--cate-id", default=None,
                        help="三级类目 ID，如 601284=女士毛衣与针织衫（推荐）")
    parser.add_argument("--category", default=None,
                        help="类目名子串，如 女士毛衣与针织衫（与 --cate-id 二选一）")
    parser.add_argument("--top", type=int, default=5,
                        help="最多融入 N 个热搜词，默认 5")
    parser.add_argument("--max-len", type=int, default=200,
                        help="标题最大长度，默认 200")
    parser.add_argument("--max-words", type=int, default=6,
                        help="关键词最大词数（过滤长商品名），默认 6")
    parser.add_argument("--min-volume", type=float, default=1,
                        help="最小搜索量阈值，默认 1")
    parser.add_argument("--no-relevance", action="store_true",
                        help="关闭标题相关性过滤（默认开启，防不相关词污染标题）")
    return parser.parse_args()


def main():
    """主流程：读关键词 → 层层过滤 → 融入标题 → 打印结果。"""
    args = parse_args()

    leads = load_keywords(args.keywords)
    if not leads:
        print("关键词文件里没有 leads 数据")
        return

    require_apparel = not args.no_relevance and is_cjk_title(args.title)
    title_core = None if args.no_relevance else core_tokens(args.title)
    title_norm = None if args.no_relevance else normalize_vi(args.title)
    if require_apparel:
        # 中文标题：无法与越南语热搜词做词面交集，跳过相关性 / 属性冲突过滤，
        # 改用服饰信号词兜底（挡类目错配的非服饰词）
        title_core = None
        title_norm = None
        print("检测到中文标题：关闭相关性 / 属性冲突过滤，启用服饰信号词过滤。")
    keywords, stats = filter_keywords(
        leads,
        cate_id=args.cate_id,
        category=args.category,
        max_words=args.max_words,
        min_volume=args.min_volume,
        title_core=title_core,
        title_norm=title_norm,
        require_apparel_signal=require_apparel,
    )

    print(f"过滤统计：共 {stats['total']} 条 → 类目不符 {stats['cate']}、"
          f"品牌/店铺名 {stats['brand']}、非服饰词 {stats['non_apparel']}、"
          f"词数过长 {stats['words']}、搜索量不足 {stats['volume']}、"
          f"属性冲突 {stats['contradiction']}、"
          f"标题不相关 {stats['relevance']} → 候选 {len(keywords)} 条")
    ranked = sorted(keywords, key=lambda k: (-k.get("rel", 1), -k["volume"]))
    print("候选热搜词 Top 10（按 相关性 > 搜索量 排序）：")
    for kw in ranked[:10]:
        print(f"  [{kw['volume']:,.0f}|rel={kw.get('rel', 1)}] "
              f"{kw['name']}  ({kw['category']})")

    new_title, added = optimize_title(keywords, args.title, args.top,
                                      args.max_len)

    print("\n=== 原标题 ===")
    print(args.title)
    print(f"\n=== 优化后标题（融入 {len(added)} 个热搜词）===")
    print(new_title)
    if added:
        print("\n已融入热搜词:", " | ".join(added))
    else:
        print("\n没有可融入的相关热搜词（可尝试放宽 --cate-id / --max-words，"
              "或加 --no-relevance 关闭相关性过滤）")


if __name__ == "__main__":
    main()
