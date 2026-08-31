# -*- coding: utf-8 -*-
"""基于妙手 TikTok 采集箱「商品详情」JSON，深拷贝生成 save 用 edit.json。

开放平台保存接口为整包回写：必须把详情里的 ``shopCollectItemInfo`` 完整
回传，只改需要改的字段，否则会抹掉标题/描述/图片/规格等既有数据。本脚本
深拷贝详情对象，仅覆盖命令行指定的字段，其余原样保留：

- 包裹尺寸 packageLength/Width/Height、商品重量 weight、发货方式；
- 尺码表 sizeChartType/sizeChart（服装类目强制，需公网图片 URL）；
- 商品属性 productAttributes（如越南服装类目必填「材质」）；
- 每个有效 SKU 的 price/stock/weight，以及多仓库存映射。

属性用简化 JSON 传入，脚本自动补全为平台结构::

    [{"attributeId": "100157", "attributeName": "材质",
      "values": [{"valueId": "1001112", "valueName": "氨纶"}]}]

用法::

    py build_edit_payload.py --detail detail.json --out edit.json \
        --price 299000 --stock 555 --weight 0.4 \
        --length 30 --width 25 --height 3 \
        --size-chart-url https://.../chart.png \
        --attributes-file attrs.json
"""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def load_info(detail_path: Path) -> dict:
    """从详情响应 JSON 中取出 shopCollectItemInfo 并深拷贝。

    兼容两种落盘格式：接口原始响应（``data.shopCollectItemInfo``）或
    已经是 info 对象本身。

    Args:
        detail_path: 详情 JSON 文件路径。

    Returns:
        深拷贝后的商品信息对象。
    """
    with open(detail_path, "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "shopCollectItemInfo" in data:
        info = data["shopCollectItemInfo"]
    elif isinstance(data, dict) and "data" in data and \
            isinstance(data["data"], dict) and \
            "shopCollectItemInfo" in data["data"]:
        info = data["data"]["shopCollectItemInfo"]
    else:
        info = data  # 已是 info 对象
    return copy.deepcopy(info)


def build_attributes(raw: list) -> list:
    """把简化属性数组转换为平台 productAttributes 结构。

    Args:
        raw: 简化属性列表，元素含 attributeId/attributeName/values。

    Returns:
        平台要求的 productAttributes 列表。
    """
    result = []
    for attr in raw:
        values = attr.get("values") or attr.get("attributeValues") or []
        attr_values = [
            {"valueId": str(v.get("valueId", "")),
             "valueName": v.get("valueName", "")}
            for v in values
        ]
        name = attr.get("attributeName", "")
        result.append({
            "attributeId": str(attr["attributeId"]),
            "attributeName": name,
            "attributeNameAlias": attr.get("attributeNameAlias", name),
            "attributeValues": attr_values,
        })
    return result


def apply_changes(info: dict, args: argparse.Namespace) -> int:
    """按命令行参数就地修改 info 对象，返回改动的 SKU 数。

    Args:
        info: 商品信息对象（会被就地修改）。
        args: 解析后的命令行参数。

    Returns:
        实际修改的有效 SKU 数量。
    """
    # --- 物流/发货字段 ---
    if args.length is not None:
        info["packageLength"] = args.length
    if args.width is not None:
        info["packageWidth"] = args.width
    if args.height is not None:
        info["packageHeight"] = args.height
    if args.weight is not None:
        info["weight"] = args.weight
    if args.delivery_option:
        info["deliveryOptionSetType"] = args.delivery_option
    info["editModel"] = args.edit_model

    # --- 尺码表（服装类目强制；URL 必须是 JPG/PNG/WEBP 公网地址）---
    if args.size_chart_url:
        info["sizeChartType"] = "image"
        info["sizeChart"] = args.size_chart_url

    # --- 商品属性 ---
    attrs_raw = None
    if args.attributes:
        attrs_raw = json.loads(args.attributes)
    elif args.attributes_file:
        with open(args.attributes_file, "r", encoding="utf-8-sig") as fh:
            attrs_raw = json.load(fh)
    if attrs_raw is not None:
        info["productAttributes"] = build_attributes(attrs_raw)

    # --- SKU 字段：价格/库存/重量/多仓库存 ---
    changed = 0
    for sku in info.get("skuMap", {}).values():
        if str(sku.get("isDelete", "0")) == "1":
            continue  # 已删除 SKU 不动
        if args.price is not None:
            sku["price"] = args.price
            # 越南等站前台零售价取「含税价」priceIncludeVat；只改 price 会
            # 保留系统按货源价自动算的高价，导致上架价错误。目标售价即买家
            # 实付含税价，故同步覆盖 priceIncludeVat。
            sku["priceIncludeVat"] = args.price
        if args.stock is not None:
            sku["stock"] = args.stock
        if args.weight is not None:
            sku["weight"] = args.weight
        if args.stock is not None:
            # 多仓库存映射同步为目标库存（值为字符串）
            wh_map = sku.get("shopIdToWarehouseIdAndStockMap") or {}
            for warehouses in wh_map.values():
                for wh_id in warehouses:
                    warehouses[wh_id] = str(args.stock)
        changed += 1
    return changed


def main() -> None:
    """命令行入口：读详情、改字段、写 edit.json 并打印核对摘要。"""
    parser = argparse.ArgumentParser(
        description="深拷贝妙手 TikTok 详情生成 save 用 edit.json")
    parser.add_argument("--detail", required=True, help="商品详情 JSON 路径")
    parser.add_argument("--out", required=True, help="输出 edit.json 路径")
    parser.add_argument("--price", type=int, help="目标售价（本币，如 VND）")
    parser.add_argument("--stock", type=int, help="目标库存（各 SKU 统一）")
    parser.add_argument("--weight", type=float, help="重量 kg")
    parser.add_argument("--length", type=int, help="包裹长 cm")
    parser.add_argument("--width", type=int, help="包裹宽 cm")
    parser.add_argument("--height", type=int, help="包裹高 cm")
    parser.add_argument("--size-chart-url", help="尺码表公网图片 URL")
    parser.add_argument("--attributes", help="商品属性简化 JSON 字符串")
    parser.add_argument("--attributes-file", help="商品属性 JSON 文件路径")
    parser.add_argument("--delivery-option", default="default",
                        choices=["default", "shipping"],
                        help="发货方式（默认 default）")
    parser.add_argument("--edit-model", default="shop",
                        choices=["shop", "site"], help="编辑模式")
    args = parser.parse_args()

    info = load_info(Path(args.detail))
    changed = apply_changes(info, args)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(info, fh, ensure_ascii=False, indent=2)

    print(f"已生成 {out_path}")
    print(f"修改 SKU 数: {changed}")
    if args.length is not None:
        print(f"包裹尺寸: {args.length}x{args.width}x{args.height} cm")
    if args.weight is not None:
        print(f"重量: {args.weight} kg")
    if args.price is not None:
        print(f"售价: {args.price}, 库存: {args.stock}")
    if args.size_chart_url:
        print(f"尺码表: {args.size_chart_url}")
    if "productAttributes" in info:
        print(f"商品属性: {len(info['productAttributes'])} 个")
    # 保留字段核对（防止整包回写抹数据）
    imgs = info.get("imgUrls") or info.get("images") or []
    specs = info.get("skuPropertyList") or info.get("skuProperty") or []
    print(f"保留: 标题长度={len(info.get('title', ''))}, 图片={len(imgs)}, "
          f"规格组={len(specs)}, 类目cid={info.get('cid')}")


if __name__ == "__main__":
    main()
