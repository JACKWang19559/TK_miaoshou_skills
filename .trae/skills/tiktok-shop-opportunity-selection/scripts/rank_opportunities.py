# -*- coding: utf-8 -*-
"""对抓取到的 TikTok 商品机会线索打分排序，输出选品清单。

输入：fetch_leads.py 生成的 JSON（含 ``leads`` 数组）。
输出：按策略打分排序后的 Top N 清单，可打印为表格，也可导出排序后的 JSON。

评分维度（原始字段多为越南语千分位格式的字符串，见 references/api-fields.md）：
- 需求热度：search_volume（搜索量）
- 销量热度：l30d_sales_volume（近 30 天销量）
- 增长趋势：l30d_sales_volume_ring_ratio（销量环比，负值为下滑）
- 蓝海程度：online_products（在线商品数，越少竞争越小）

用法：
    py rank_opportunities.py --input opportunity_leads.json \
        [--strategy balanced] [--top 20] [--out ranked.json]
"""
import argparse
import json
import math
import re

# 千分位格式：1.234 / 12.345 / 123.456（越南语用 . 作千分位分隔符）
_THOUSANDS_RE = re.compile(r"-?\d{1,3}(\.\d{3})+")


def parse_num(value):
    """把越南语千分位格式的数值字符串解析为 float。

    规则：形如 ``1.234`` / ``12.345`` 的字符串按千分位处理（去点）；
    其余去除货币符号与逗号后直接转 float；无法解析时返回 0.0。

    Args:
        value: 字符串或数值，可能为 None / 空串。

    Returns:
        解析后的浮点数。
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


def _log1p(value):
    """对非负值取 log1p，负值取 -log1p(-value)，用于压缩量纲。"""
    if value >= 0:
        return math.log1p(value)
    return -math.log1p(-value)


def score(lead, strategy):
    """计算一条 lead 的综合得分。

    Args:
        lead: 单条 lead 字典。
        strategy: 选品策略（hot / rising / blue_ocean / balanced）。

    Returns:
        0-100 区间的综合得分。
    """
    search = parse_num(lead.get("search_volume"))
    sales = parse_num(lead.get("l30d_sales_volume"))
    ratio = parse_num(lead.get("l30d_sales_volume_ring_ratio"))
    online = max(parse_num(lead.get("online_products")), 1)

    demand = _log1p(search)
    sales_h = _log1p(sales)
    growth = max(min(_log1p(ratio), 10), -10)
    blue = _log1p(1.0 / online)

    if strategy == "hot":
        parts = [(sales_h, 0.5), (demand, 0.3), (growth, 0.2)]
    elif strategy == "rising":
        parts = [(growth, 0.6), (sales_h, 0.2), (demand, 0.2)]
    elif strategy == "blue_ocean":
        parts = [(blue, 0.5), (demand, 0.3), (sales_h, 0.2)]
    else:  # balanced
        parts = [(sales_h, 0.3), (demand, 0.3), (growth, 0.2), (blue, 0.2)]

    return sum(weight * value for value, weight in parts)


def _reason(lead):
    """生成一条可读的推荐理由。"""
    reasons = []
    if parse_num(lead.get("l30d_sales_volume_ring_ratio")) > 20:
        reasons.append("销量环比快速增长，处于起量期")
    if parse_num(lead.get("online_products")) <= 5:
        reasons.append("在线商品少，竞争度低（蓝海）")
    if parse_num(lead.get("search_volume")) > 1000:
        reasons.append("搜索需求旺盛")
    if parse_num(lead.get("l30d_sales_volume")) > 500:
        reasons.append("近 30 天销量已跑量")
    return "；".join(reasons) if reasons else "综合指标较均衡"


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="商品机会选品打分排序")
    parser.add_argument("--input", required=True, help="fetch_leads.py 输出的 JSON 文件")
    parser.add_argument("--strategy", default="balanced",
                        choices=["hot", "rising", "blue_ocean", "balanced"],
                        help="选品策略：hot=追爆款, rising=起量, blue_ocean=蓝海, balanced=均衡")
    parser.add_argument("--top", type=int, default=20, help="输出前 N 条，默认 20")
    parser.add_argument("--out", default=None, help="可选，把排序结果导出为 JSON")
    return parser.parse_args()


def main():
    """主流程：读取 → 打分 → 排序 → 打印清单（可选导出）。"""
    args = parse_args()

    with open(args.input, encoding="utf-8") as fh:
        raw = json.load(fh)
    leads = raw.get("leads", [])

    if not leads:
        print("输入文件里没有 leads 数据")
        return

    ranked = []
    for lead in leads:
        ranked.append((score(lead, args.strategy), lead))

    ranked.sort(key=lambda pair: pair[0], reverse=True)

    print(f"策略={args.strategy}，共 {len(ranked)} 条，展示前 {args.top} 条\n")
    header = ("排名 | 综合分 | 商机名 | 类目 | 搜索量 | 近30天销量 | 环比% | 在线商品数 | 建议价")
    print(header)
    print("-" * len(header))
    for i, (sc, lead) in enumerate(ranked[:args.top], start=1):
        cate = "/".join(filter(None, [
            lead.get("level1_cate_name"),
            lead.get("level2_cate_name"),
            lead.get("level3_cate_name"),
        ]))
        price_low = parse_num(lead.get("recommend_price_low"))
        price_high = parse_num(lead.get("recommend_price_high"))
        currency = lead.get("curreny", "")
        price = f"{price_low:,.0f}-{price_high:,.0f}{currency}" if price_high else "-"
        name = (lead.get("lead_name") or "")[:28]
        print(f"{i:>3} | {sc:5.1f} | {name} | {cate[:20]} | "
              f"{parse_num(lead.get('search_volume')):,.0f} | "
              f"{parse_num(lead.get('l30d_sales_volume')):,.0f} | "
              f"{parse_num(lead.get('l30d_sales_volume_ring_ratio')):,.0f} | "
              f"{parse_num(lead.get('online_products')):,.0f} | {price}")
        print(f"     理由: {_reason(lead)}")

    if args.out:
        output = {
            "strategy": args.strategy,
            "ranked": [
                {"score": sc, "lead": lead}
                for sc, lead in ranked[:args.top]
            ],
        }
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(output, fh, ensure_ascii=False, indent=2)
        print(f"\n已导出排序结果: {args.out}")


if __name__ == "__main__":
    main()
