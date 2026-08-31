# -*- coding: utf-8 -*-
"""TikTok 越南站跨境定价计算器（人民币成本 -> 越南盾建议售价）。

依据移植自货叮咚生产环境的越南站定价模板（``pricing_template_vn.json``），
按"单位经济模型"计算保本价、目标利润价，并输出越南盾心理尾价。

模型（所有百分比费率均以售价为基数）::

    总变动费率 = 平台佣金 + 交易手续费 + 提现 + VAT + 达人佣金(可选)
    卖家单位成本(CNY) = 商品成本 + 订单处理费 + 货代费 + 其它 + 头程运费(卖家担)
                       注：尾程运费买家付，不计入卖家成本
    保本价(CNY)   = 卖家单位成本 / (1 - 总变动费率)
    目标利润价    = 卖家单位成本 / (1 - 总变动费率 - 目标利润率)
    售价(VND)     = CNY价 * 汇率，再按千越南盾 + x9000 心理尾价取整

用法示例::

    py vn_pricing.py --cost 28.5 --weight 0.35
    py vn_pricing.py --cost 28.5 --head-leg 9.5 --no-affiliate
    py vn_pricing.py --cost 18 --margin 0.18
"""

import argparse
import json
import os
import sys

# 模板默认与脚本同目录
DEFAULT_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "pricing_template_vn.json")


def load_template(path):
    """读取定价模板 JSON。

    :param path: 模板文件路径
    :return: 模板字典
    """
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def total_rate(template, use_affiliate=True):
    """汇总以售价为基数的变动费率。

    :param template: 模板字典
    :param use_affiliate: 是否计入达人佣金（联盟订单才产生）
    :return: 总费率（小数，如 0.421）及明细列表
    """
    rates = template["rate_components"]
    detail = []
    total = 0.0
    for key, comp in rates.items():
        val = float(comp.get("value", 0))
        # 达人佣金可按是否走联盟开关
        if key == "affiliate_commission_rate" and not use_affiliate:
            detail.append((comp["label"], 0.0, "不计（无联盟订单）"))
            continue
        total += val
        detail.append((comp["label"], val, comp.get("source", "")))
    return total, detail


def seller_unit_cost_cny(template, product_cost, head_leg_cny):
    """计算卖家单位成本（人民币）。

    :param template: 模板字典
    :param product_cost: 商品采购成本（CNY）
    :param head_leg_cny: 头程运费（CNY，卖家承担，按重量查官方运价）
    :return: 单位成本（CNY）及明细列表
    """
    fixed = template["fixed_costs_cny"]
    parts = [
        ("商品采购成本", product_cost),
        ("订单处理费", float(fixed["order_processing_fee"]["value"])),
        ("货代费用", float(fixed["freight_forwarder_fee"]["value"])),
        ("其它费用", float(fixed["other_fee"]["value"])),
        ("国内段运费", float(fixed["domestic_shipping_fee"]["value"])),
        ("头程运费(卖家担)", head_leg_cny),
    ]
    total = sum(v for _, v in parts)
    return total, parts


def price_for_target(cost_cny, rate_total, target_margin):
    """按目标利润率反推售价（CNY）。

    保本价对应 target_margin=0。

    :param cost_cny: 卖家单位成本（CNY）
    :param rate_total: 总变动费率（小数）
    :param target_margin: 目标贡献利润率（小数）；保本传 0
    :return: 售价（CNY，未取整）
    """
    denom = 1.0 - rate_total - target_margin
    if denom <= 0:
        raise ValueError("费率与目标利润率之和 >= 100%，无法定价，请检查模板。")
    return cost_cny / denom


def to_vnd_with_tail(price_cny, fx, tail_cfg, floor_vnd=0):
    """人民币价转越南盾，并做千位 + 心理尾价取整。

    心理尾价为末位落在 9 的千位数（即结尾 9,000，如 299,000 / 309,000）。
    优先取不高于换算价的最近 x9,000（让价格显得更低）；若该价低于保底
    价（默认保本价），则进位到上一个 x9,000 以守住利润。

    :param price_cny: 售价（CNY）
    :param fx: 汇率（1 CNY = fx VND）
    :param tail_cfg: 尾价配置（round_to / psychological_tail）
    :param floor_vnd: 保底越南盾价；取整结果不得低于此值（0 表示不限制）
    :return: (取整后越南盾售价, 原始换算越南盾价)
    """
    import math

    raw_vnd = price_cny * fx
    round_to = int(tail_cfg["round_to"])      # 1000
    tail = int(tail_cfg["psychological_tail"])  # 9000
    # 以 round_to 为单位，末位需等于 tail/round_to（9000/1000=9）
    tail_digit = tail // round_to             # 9
    n = raw_vnd / round_to
    # 不高于 n 的最近一个"末位为 tail_digit"的整数
    down = math.floor((n + 1) / (tail_digit + 1)) * (tail_digit + 1) - 1
    candidate = down * round_to
    # 低于保底价则进位到上一个同尾价
    if candidate < floor_vnd:
        candidate = (down + tail_digit + 1) * round_to
    return int(candidate), int(raw_vnd)


def main():
    """命令行入口：解析参数、计算并打印定价方案。"""
    parser = argparse.ArgumentParser(
        description="TikTok越南站跨境定价计算器（CNY成本 -> VND建议售价）")
    parser.add_argument("--cost", type=float, required=True,
                        help="商品采购成本（人民币CNY），如 28.5")
    parser.add_argument("--weight", type=float, default=None,
                        help="商品包裹重量（KG），用于提示头程运费核实")
    parser.add_argument("--head-leg", type=float, default=None,
                        help="头程运费（CNY/件）。不传则用模板默认值（轻小件占位）")
    parser.add_argument("--margin", type=float, default=None,
                        help="自定义目标利润率（小数，如0.18）。不传则输出三档场景")
    parser.add_argument("--no-affiliate", action="store_true",
                        help="不计达人佣金（新店无联盟订单时使用，价格更低）")
    parser.add_argument("--template", default=DEFAULT_TEMPLATE,
                        help="定价模板JSON路径")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    tpl = load_template(args.template)
    fx = float(tpl["fx"]["cny_to_vnd"])
    use_aff = not args.no_affiliate

    # 头程运费：命令行 > 模板默认
    if args.head_leg is not None:
        head_leg = args.head_leg
        head_src = "命令行指定"
    else:
        head_leg = float(tpl["logistics"]["head_leg"]["default_cny_per_item"])
        head_src = "模板默认(占位,需按官方运价核实)"

    rate_total, rate_detail = total_rate(tpl, use_affiliate=use_aff)
    unit_cost, cost_parts = seller_unit_cost_cny(tpl, args.cost, head_leg)

    print("=" * 72)
    print(f"  TikTok越南站定价方案  |  成本 {args.cost} CNY"
          f"  |  汇率 1CNY={fx:.0f}VND  |  达人佣金:{'计' if use_aff else '不计'}")
    print("=" * 72)

    print("\n【变动费率】（以售价为基数）")
    for label, val, _ in rate_detail:
        if val > 0:
            print(f"  {label:<12}: {val*100:>5.1f}%")
    print(f"  {'合计':<12}: {rate_total*100:>5.1f}%")

    print("\n【卖家单位成本】(CNY，尾程运费买家付不计入)")
    for label, val in cost_parts:
        if val != 0:
            print(f"  {label:<14}: {val:>7.2f}")
    print(f"  {'单位成本合计':<14}: {unit_cost:>7.2f} CNY")
    print(f"  (头程运费来源: {head_src}"
          f"{f'，重量{args.weight}KG' if args.weight else ''}，请按官方运价表核实)")

    # 保本价（CNY 与 VND）。VND 保本价取整时以自身换算价为保底，只上不下。
    be_cny = price_for_target(unit_cost, rate_total, 0.0)
    be_vnd, be_raw = to_vnd_with_tail(be_cny, fx, tpl["price_tail_vnd"],
                                      floor_vnd=be_cny * fx)

    print("\n【定价方案】")
    scenarios = tpl["target_margin_scenarios"]
    if args.margin is not None:
        rows = [("自定义", args.margin)]
    else:
        rows = [(scenarios["traffic"]["label"], scenarios["traffic"]["margin"]),
                (scenarios["normal"]["label"], scenarios["normal"]["margin"]),
                (scenarios["premium"]["label"], scenarios["premium"]["margin"])]

    print(f"  {'场景':<22}{'利润率':>6}{'CNY价':>10}{'建议售价VND':>14}{'单件利润CNY':>12}")
    print("  " + "-" * 66)
    for label, margin in rows:
        p_cny = price_for_target(unit_cost, rate_total, margin)
        # 取整不得低于保本价，守住不亏底线
        p_vnd, raw_vnd = to_vnd_with_tail(p_cny, fx, tpl["price_tail_vnd"],
                                          floor_vnd=be_vnd)
        # 实际单件利润（按取整后VND价折回CNY估算贡献利润）
        realized_price_cny = p_vnd / fx
        profit_cny = realized_price_cny * (1 - rate_total) - unit_cost
        print(f"  {label:<22}{margin*100:>5.0f}%{p_cny:>10.1f}"
              f"{p_vnd:>14,}{profit_cny:>12.2f}")

    print(f"\n  保本价: {be_cny:.1f} CNY ≈ {be_vnd:,} VND（低于此价必亏）")
    if not use_aff:
        print("  提示: 当前未计达人佣金；若后续开联盟带货，实际费率+10%，建议按含佣价上架。")
    print("=" * 72)


if __name__ == "__main__":
    main()
