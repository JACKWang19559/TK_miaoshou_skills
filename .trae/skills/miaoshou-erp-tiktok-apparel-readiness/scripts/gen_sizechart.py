# -*- coding: utf-8 -*-
"""生成 TikTok 服装商品尺码表图（PNG）。

妙手/TikTok 服装类目（如越南站 cid 601284）强制要求尺码表，且开放平台
只接受公网图片 URL。货源 1688 常无尺码图，本脚本按站点语言预设生成
一张白底、品牌色表头的标准尺码表，供后续上传图床并写入 ``sizeChart``。

用法示例::

    py gen_sizechart.py --site VN --out sizechart.png
    py gen_sizechart.py --data my_sizes.json --out sizechart.png

``--data`` JSON 结构（可选，缺省用站点预设）::

    {
      "title": "BẢNG SIZE / SIZE CHART",
      "subtitle": "Áo Polo Nữ ...",
      "headers": ["Size", "Vòng ngực\\n(cm)", ...],
      "rows": [["S", "86", "56", ...], ...],
      "notes": ["* Đơn vị: cm ...", ...],
      "accent": [31, 58, 95]
    }
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Windows 自带字体目录（Arial 支持越南语等拉丁扩展字符）
FONT_DIR = r"C:\Windows\Fonts"

# 画布默认尺寸
CANVAS_W = 800
MARGIN_X = 50
TABLE_TOP = 170
HEAD_H = 64
ROW_H = 62

# 配色（RGB）
WHITE = (255, 255, 255)
LIGHT = (242, 245, 249)
BORDER = (201, 210, 221)
TEXT = (40, 48, 63)
NOTE_GRAY = (120, 128, 140)
DEFAULT_ACCENT = (31, 58, 95)  # 藏青

# 各站点语言预设：女装针织/梭织上衣通用参考尺寸（单位 cm，平铺测量）
PRESETS = {
    "VN": {
        "title": "BẢNG SIZE / SIZE CHART",
        "subtitle": "Áo Polo Nữ Dệt Kim - Size S đến 3XL",
        "headers": ["Size", "Vòng ngực\n(cm)", "Dài áo\n(cm)",
                    "Rộng vai\n(cm)", "Dài tay\n(cm)"],
        "col_w": [90, 155, 155, 150, 150],
        "rows": [
            ["S", "86", "56", "35", "17"],
            ["M", "90", "58", "36", "18"],
            ["L", "94", "60", "37", "18"],
            ["XL", "98", "62", "38", "19"],
            ["2XL", "104", "64", "40", "20"],
            ["3XL", "110", "66", "42", "20"],
        ],
        "notes": [
            "* Đơn vị: cm. Số đo nằm ngang khi đặt phẳng áo.",
            "* Dung sai 1-3cm do đo thủ công, vui lòng tham khảo",
            "  bảng size trước khi đặt hàng.",
        ],
        "accent": list(DEFAULT_ACCENT),
    },
}


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """加载字体，缺失时回退到 PIL 默认字体。

    Args:
        name: 字体文件名（位于 ``FONT_DIR``）。
        size: 字号。

    Returns:
        PIL 字体对象。
    """
    try:
        return ImageFont.truetype(str(Path(FONT_DIR) / name), size)
    except OSError:
        return ImageFont.load_default()


def draw_centered(draw, cx, cy, text, font, fill):
    """在 (cx, cy) 处居中绘制多行文本。

    Args:
        draw: ``ImageDraw.Draw`` 对象。
        cx: 中心 x 坐标。
        cy: 中心 y 坐标。
        text: 文本（可含 ``\\n`` 换行）。
        font: 字体对象。
        fill: 填充色。
    """
    lines = text.split("\n")
    line_h = font.size + 6
    y = cy - line_h * len(lines) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text((cx - (bbox[2] - bbox[0]) / 2, y), line, font=font, fill=fill)
        y += line_h


def render(spec: dict, out_path: Path) -> None:
    """按规格字典绘制尺码表并保存 PNG。

    Args:
        spec: 含 title/subtitle/headers/rows/notes/col_w/accent 的规格。
        out_path: 输出 PNG 路径。
    """
    accent = tuple(spec.get("accent", DEFAULT_ACCENT))
    headers = spec["headers"]
    rows = spec["rows"]
    col_w = spec.get("col_w")
    if not col_w:
        # 未指定列宽时均分布局
        total = CANVAS_W - 2 * MARGIN_X
        col_w = [total // len(headers)] * len(headers)

    table_h = HEAD_H + ROW_H * len(rows)
    note_h = 28 * len(spec.get("notes", [])) + 40
    height = TABLE_TOP + table_h + note_h

    img = Image.new("RGB", (CANVAS_W, height), WHITE)
    draw = ImageDraw.Draw(img)

    f_title = load_font("arialbd.ttf", 40)
    f_sub = load_font("arial.ttf", 22)
    f_head = load_font("arialbd.ttf", 21)
    f_cell = load_font("arial.ttf", 22)
    f_size = load_font("arialbd.ttf", 24)
    f_note = load_font("arial.ttf", 18)

    # 标题
    bbox = draw.textbbox((0, 0), spec["title"], font=f_title)
    draw.text(((CANVAS_W - (bbox[2] - bbox[0])) / 2, 48),
              spec["title"], font=f_title, fill=accent)
    if spec.get("subtitle"):
        bbox = draw.textbbox((0, 0), spec["subtitle"], font=f_sub)
        draw.text(((CANVAS_W - (bbox[2] - bbox[0])) / 2, 108),
                  spec["subtitle"], font=f_sub, fill=TEXT)

    x0, x1 = MARGIN_X, MARGIN_X + sum(col_w)
    # 表头背景
    draw.rectangle([x0, TABLE_TOP, x1, TABLE_TOP + HEAD_H], fill=accent)

    # 各列中心 x
    centers, x = [], x0
    for w in col_w:
        centers.append(x + w / 2)
        x += w

    for i, head in enumerate(headers):
        draw_centered(draw, centers[i], TABLE_TOP + HEAD_H / 2,
                      head, f_head, WHITE)

    # 数据行（斑马纹）
    for r, row in enumerate(rows):
        y0 = TABLE_TOP + HEAD_H + r * ROW_H
        if r % 2 == 1:
            draw.rectangle([x0, y0, x1, y0 + ROW_H], fill=LIGHT)
        for c, val in enumerate(row):
            font = f_size if c == 0 else f_cell
            color = accent if c == 0 else TEXT
            draw_centered(draw, centers[c], y0 + ROW_H / 2, val, font, color)

    # 边框与网格线
    bottom = TABLE_TOP + HEAD_H + len(rows) * ROW_H
    draw.rectangle([x0, TABLE_TOP, x1, bottom], outline=BORDER, width=2)
    for r in range(len(rows) + 1):
        y = TABLE_TOP + HEAD_H + r * ROW_H
        draw.line([x0, y, x1, y], fill=BORDER, width=1)
    x = x0
    for w in col_w[:-1]:
        x += w
        draw.line([x, TABLE_TOP, x, bottom], fill=BORDER, width=1)

    # 脚注
    ny = bottom + 28
    for note in spec.get("notes", []):
        draw.text((x0 + 4, ny), note, font=f_note, fill=NOTE_GRAY)
        ny += 28

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")


def main() -> None:
    """命令行入口：解析参数、选预设/读自定义数据并渲染。"""
    parser = argparse.ArgumentParser(description="生成 TikTok 服装尺码表 PNG")
    parser.add_argument("--site", default="VN",
                        help="站点预设（默认 VN，内置越南语女装上衣）")
    parser.add_argument("--data", help="自定义尺码 JSON 文件路径（覆盖预设）")
    parser.add_argument("--out", required=True, help="输出 PNG 路径")
    args = parser.parse_args()

    if args.data:
        with open(args.data, "r", encoding="utf-8-sig") as fh:
            spec = json.load(fh)
    else:
        site = args.site.upper()
        if site not in PRESETS:
            sys.exit(f"未内置站点 {site} 的预设，请用 --data 传入自定义尺码 JSON")
        spec = PRESETS[site]

    render(spec, Path(args.out))
    print(f"已生成尺码表: {args.out}")
    print(f"站点预设: {args.site or 'custom'}, 尺码行数: {len(spec['rows'])}")


if __name__ == "__main__":
    main()
