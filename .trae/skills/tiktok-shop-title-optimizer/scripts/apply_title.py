# -*- coding: utf-8 -*-
"""用热搜词优化 TikTok 采集箱商品标题，并把新标题写回妙手 ERP。

完整闭环：
    查商品详情（复用 miaoshou-erp-tiktok-product-edit 的 tiktok_collectbox.py）
    → 取当前标题 + 三级类目 ID
    → 用 optimize_title 五级过滤热搜词、融入标题
    → dry-run 预览（默认不写）
    → --execute 时深拷贝详情对象只改 title 字段，整包写回
    → 重新拉详情校验标题已更新。

安全边界：
    - 只改 title 一个字段，其余价格/库存/图片/属性/SKU 原样保留；
    - 写回双门：命令行显式 --execute + 对话层人工确认；
    - 凭证走妙手技能现有配置（config.json / 环境变量），本脚本不接触密钥；
    - 候选词为 0、标题超长、或新旧标题一致时中止，不写。

用法：
    py apply_title.py --detail-id 3134788019 --keywords keyword_unmet.json --site VN
    py apply_title.py --detail-id 3134788019 --keywords keyword_unmet.json --site VN --execute
    py apply_title.py --detail-id 3134788019 --keywords keyword_unmet.json \
        --mode shop --shop-id 1001 --execute
"""
import argparse
import copy
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# 同目录 import optimize_title（过滤 / 融入函数）
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import optimize_title  # noqa: E402

# 妙手采集箱脚本默认位置：../../miaoshou-erp-tiktok-product-edit/scripts/tiktok_collectbox.py
DEFAULT_COLLECTBOX_SCRIPT = (
    _HERE.parent.parent
    / "miaoshou-erp-tiktok-product-edit"
    / "scripts"
    / "tiktok_collectbox.py"
)

# 妙手返回的 cid 可能是纯数字（601284）或带前缀（magellan_601284），取最长数字段
_CID_RE = re.compile(r"\d{4,}")


def run_subprocess(args_list):
    """执行子进程命令并返回 (returncode, stdout, stderr)。

    用当前解释器并开启 UTF-8 模式，避免 Windows 下中文输出乱码。

    Args:
        args_list: 完整命令行参数列表（不含解释器）。

    Returns:
        三元组 (returncode, stdout, stderr)。
    """
    cmd = [sys.executable, "-X", "utf8"] + args_list
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.returncode, result.stdout, result.stderr


def fetch_detail(script, detail_id, mode, site=None, shop_id=None):
    """调用 tiktok_collectbox.py detail 拉详情 JSON。

    Args:
        script: tiktok_collectbox.py 路径。
        detail_id: 采集箱详情 ID。
        mode: "site" 或 "shop"。
        site: 站点代码（site 模式）。
        shop_id: 店铺 ID（shop 模式）。

    Returns:
        完整响应 dict（含 result / code / data）。

    Raises:
        RuntimeError: 子进程失败或无法解析 JSON 时。
    """
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "detail.json"
        cmd = [str(script), "-o", str(out_path), "detail", str(detail_id),
               "--mode", mode]
        if mode == "site":
            cmd += ["--site", site]
        else:
            cmd += ["--shop-id", str(shop_id)]
        code, stdout, stderr = run_subprocess(cmd)
        if code != 0:
            raise RuntimeError(f"detail 失败:\n{stdout}\n{stderr}")
        if not out_path.exists():
            raise RuntimeError("detail 未生成输出文件")
        with open(out_path, encoding="utf-8") as fh:
            return json.load(fh)


def fetch_title_and_cid(detail, mode):
    """从详情响应中提取 (ossMd5, info, title, cid)。

    Args:
        detail: fetch_detail 返回的完整响应。
        mode: "site" 或 "shop"。

    Returns:
        四元组 (oss_md5, info, title, cid)。
        - info 为 shopCollectItemInfo 或 siteCollectItemInfo 对象；
        - cid 为提取出的类目 ID 字符串，无类目时为 None。
    """
    data = detail.get("data") or {}
    oss_md5 = data.get("ossMd5")
    key = "siteCollectItemInfo" if mode == "site" else "shopCollectItemInfo"
    info = data.get(key) or {}
    title = (info.get("title") or "").strip()
    raw_cid = info.get("cid") or ""
    match = _CID_RE.search(str(raw_cid))
    cid = match.group(0) if match else None
    return oss_md5, info, title, cid


def build_new_title(keywords_path, title, cate_id, top, max_words,
                    max_len, min_volume):
    """五级过滤热搜词并生成新标题。

    Args:
        keywords_path: 热搜词 JSON 文件路径。
        title: 原标题。
        cate_id: 三级类目 ID（None 则跳过类目硬过滤，仅靠相关性）。
        top: 最多融入词数。
        max_words: 关键词最大词数。
        max_len: 标题最大长度。
        min_volume: 最小搜索量。

    Returns:
        四元组 (new_title, added, stats, candidate_count)。
        - new_title: 优化后标题；
        - added: 已融入的关键词列表；
        - stats: 过滤统计 dict；
        - candidate_count: 过滤后候选关键词数。
    """
    leads = optimize_title.load_keywords(keywords_path)
    is_cjk = optimize_title.is_cjk_title(title)
    if is_cjk:
        # 中文标题：无法与越南语热搜词做词面交集，跳过相关性 / 属性冲突过滤，
        # 改用服饰信号词兜底（挡类目错配的非服饰词）
        title_core = None
        title_norm = None
    else:
        title_core = optimize_title.core_tokens(title)
        title_norm = optimize_title.normalize_vi(title)
    keywords, stats = optimize_title.filter_keywords(
        leads,
        cate_id=cate_id,
        max_words=max_words,
        min_volume=min_volume,
        title_core=title_core,
        title_norm=title_norm,
        require_apparel_signal=is_cjk,
    )
    new_title, added = optimize_title.optimize_title(
        keywords, title, top=top, max_len=max_len,
    )
    return new_title, added, stats, len(keywords)


def save_title(script, detail_id, mode, oss_md5, info, site=None, shop_id=None):
    """深拷贝 info 对象只改 title 字段后写回妙手。

    Args:
        script: tiktok_collectbox.py 路径。
        detail_id: 采集箱详情 ID。
        mode: "site" 或 "shop"。
        oss_md5: 详情接口返回的 ossMd5。
        info: 完整 info 对象（已改 title）。
        site: 站点代码（site 模式）。
        shop_id: 店铺 ID（shop 模式）。

    Returns:
        完整响应 dict。

    Raises:
        RuntimeError: 子进程失败时。
    """
    with tempfile.TemporaryDirectory() as tmp:
        edit_path = Path(tmp) / "edit.json"
        with open(edit_path, "w", encoding="utf-8") as fh:
            json.dump(info, fh, ensure_ascii=False)
        cmd = [str(script), "save", str(detail_id), "--mode", mode,
               "--oss-md5", str(oss_md5), "--file", str(edit_path)]
        if mode == "site":
            cmd += ["--site", site]
        else:
            cmd += ["--shop-id", str(shop_id)]
        code, stdout, stderr = run_subprocess(cmd)
        if code != 0:
            raise RuntimeError(f"save 失败:\n{stdout}\n{stderr}")
        return {"stdout": stdout}


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="热搜词优化 TikTok 采集箱商品标题并写回妙手",
    )
    parser.add_argument("--detail-id", required=True, help="采集箱详情 ID")
    parser.add_argument("--mode", choices=["site", "shop"], default="site",
                        help="编辑模式：site=站点模式（默认），shop=店铺模式")
    parser.add_argument("--site", default=None,
                        help="站点代码（site 模式必填，如 VN）")
    parser.add_argument("--shop-id", default=None,
                        help="店铺 ID（shop 模式必填）")
    parser.add_argument("--keywords", required=True,
                        help="热搜词 JSON（fetch_leads.py 输出）")
    parser.add_argument("--cate-id", default=None,
                        help="覆盖商品三级类目 ID（默认从详情 cid 自动提取）")
    parser.add_argument("--top", type=int, default=5,
                        help="最多融入热搜词数，默认 5")
    parser.add_argument("--max-words", type=int, default=6,
                        help="关键词最大词数，默认 6")
    parser.add_argument("--max-len", type=int, default=255,
                        help="标题最大长度，默认 255（TikTok 上限）")
    parser.add_argument("--min-volume", type=float, default=1,
                        help="最小搜索量阈值，默认 1")
    parser.add_argument("--execute", action="store_true",
                        help="执行写回（默认 dry-run 只预览）")
    parser.add_argument("--collectbox-script",
                        default=str(DEFAULT_COLLECTBOX_SCRIPT),
                        help="tiktok_collectbox.py 路径（默认自动定位）")
    return parser.parse_args()


def main():
    """主流程：查详情 → 优化标题 → 预览/写回 → 复查。"""
    args = parse_args()

    # 模式参数校验
    if args.mode == "site" and not args.site:
        print("ERROR: site 模式必须传 --site（如 VN）")
        sys.exit(1)
    if args.mode == "shop" and not args.shop_id:
        print("ERROR: shop 模式必须传 --shop-id")
        sys.exit(1)

    script = Path(args.collectbox_script)
    if not script.exists():
        print(f"ERROR: 找不到采集箱脚本 {script}")
        print("请用 --collectbox-script 指定 tiktok_collectbox.py 路径")
        sys.exit(1)

    # 1. 查详情
    detail = fetch_detail(script, args.detail_id, args.mode,
                          site=args.site, shop_id=args.shop_id)
    oss_md5, info, old_title, cid = fetch_title_and_cid(detail, args.mode)
    if not old_title:
        print("ERROR: 商品无标题，无法优化")
        sys.exit(1)

    cate_id = args.cate_id or cid
    print(f"商品 {args.detail_id} | 模式 {args.mode} | 类目 ID: {cate_id or '（未知，改用相关性过滤）'}")
    print(f"原标题: {old_title}\n")

    # 2. 优化标题
    new_title, added, stats, candidate_count = build_new_title(
        args.keywords, old_title, cate_id, args.top,
        args.max_words, args.max_len, args.min_volume,
    )
    print(f"过滤统计：共 {stats['total']} 条 → 类目不符 {stats['cate']}、"
          f"品牌/店铺名 {stats['brand']}、非服饰词 {stats['non_apparel']}、"
          f"词数过长 {stats['words']}、搜索量不足 {stats['volume']}、"
          f"属性冲突 {stats['contradiction']}、"
          f"标题不相关 {stats['relevance']} → 候选 {candidate_count} 条")

    # 3. 结果校验
    if not added:
        print("\n没有可融入的相关热搜词，标题不变，未写回。")
        sys.exit(0)
    if len(new_title) > args.max_len:
        print(f"\nERROR: 优化后标题 {len(new_title)} 字符，超过上限 {args.max_len}，未写回。")
        sys.exit(1)
    if new_title == old_title:
        print("\n新旧标题一致，无需写回。")
        sys.exit(0)

    print(f"\n=== 优化后标题（融入 {len(added)} 个热搜词）===")
    print(new_title)
    print("\n已融入热搜词:", " | ".join(added))
    print(f"\n新标题长度: {len(new_title)} 字符")

    # 4. dry-run 预览
    if not args.execute:
        print("\n[DRY-RUN] 未写回。确认无误后加 --execute 执行写回。")
        sys.exit(0)

    # 5. 写回（深拷贝只改 title；补齐缺失的必填发货方式字段）
    new_info = copy.deepcopy(info)
    new_info["title"] = new_title
    if not new_info.get("deliveryOptionSetType"):
        # deliveryOptionSetType 是 save 必填字段，采集/认领后可能缺失，补默认值
        new_info["deliveryOptionSetType"] = "default"
        print("提示：deliveryOptionSetType 缺失，已补默认值 default。")
    print("\n写回中（仅修改 title 字段，其余字段原样保留）...")
    save_title(script, args.detail_id, args.mode, oss_md5, new_info,
               site=args.site, shop_id=args.shop_id)
    print("写回成功。")

    # 6. 复查
    detail_after = fetch_detail(script, args.detail_id, args.mode,
                                site=args.site, shop_id=args.shop_id)
    _, _, title_after, _ = fetch_title_and_cid(detail_after, args.mode)
    if title_after == new_title:
        print(f"✅ 复查通过：标题已更新为「{title_after}」")
    else:
        print(f"⚠️ 复查异常：期望「{new_title}」，实际「{title_after}」")


if __name__ == "__main__":
    main()
