# -*- coding: utf-8 -*-
"""把本地图片上传到免登录公网图床，返回可直接访问的图片直链。

妙手/TikTok 开放平台的尺码表、补充图片等字段只接受公网 URL，本脚本把
本地 PNG/JPG/WEBP 上传到匿名图床。端点按可用性顺序回退：

1. ``litterbox``（catbox 临时托管，默认 72h，免 key，本环境实测可达）；
2. ``catbox``（catbox 永久托管，免 key，但部分网络/地区不可达）。

注意：临时链接过期后图片会失效，建议在有效期内发布（发布时平台会把图
转存到自有 CDN）；如需长期链接，优先 ``--host catbox`` 或自建 OSS。

用法::

    py upload_image.py sizechart.png
    py upload_image.py sizechart.png --host catbox
    py upload_image.py sizechart.png --expire 1h
"""
import argparse
import sys

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

LITTERBOX_URL = "https://litterbox.catbox.moe/resources/internals/api.php"
CATBOX_URL = "https://catbox.moe/user/api.php"


def upload_litterbox(path: str, expire: str, timeout: int = 60) -> str:
    """上传到 litterbox 临时图床。

    Args:
        path: 本地图片路径。
        expire: 有效期，``1h`` / ``12h`` / ``24h`` / ``72h``。
        timeout: 请求超时秒数。

    Returns:
        图片直链 URL。
    """
    with open(path, "rb") as fh:
        files = {"fileToUpload": fh}
        data = {"reqtype": "fileupload", "time": expire}
        resp = requests.post(LITTERBOX_URL, data=data, files=files,
                             headers={"User-Agent": UA}, timeout=timeout)
    resp.raise_for_status()
    url = resp.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"litterbox 返回异常: {url[:200]}")
    return url


def upload_catbox(path: str, timeout: int = 60) -> str:
    """上传到 catbox 永久图床。

    Args:
        path: 本地图片路径。
        timeout: 请求超时秒数。

    Returns:
        图片直链 URL。
    """
    with open(path, "rb") as fh:
        files = {"fileToUpload": fh}
        data = {"reqtype": "fileupload"}
        resp = requests.post(CATBOX_URL, data=data, files=files,
                             headers={"User-Agent": UA}, timeout=timeout)
    resp.raise_for_status()
    url = resp.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"catbox 返回异常: {url[:200]}")
    return url


def main() -> None:
    """命令行入口：按选择/回退顺序上传并打印直链。"""
    parser = argparse.ArgumentParser(description="上传图片到公网图床拿直链")
    parser.add_argument("file", help="本地图片路径（PNG/JPG/WEBP）")
    parser.add_argument("--host", choices=["litterbox", "catbox"],
                        default="litterbox",
                        help="图床选择（默认 litterbox 临时72h；catbox 永久）")
    parser.add_argument("--expire", default="72h",
                        choices=["1h", "12h", "24h", "72h"],
                        help="litterbox 有效期（默认 72h）")
    args = parser.parse_args()

    # 指定 catbox 时只试 catbox；否则先 litterbox，失败再回退 catbox
    order = [args.host] if args.host == "catbox" else ["litterbox", "catbox"]
    last_err = None
    for host in order:
        try:
            if host == "litterbox":
                url = upload_litterbox(args.file, args.expire)
            else:
                url = upload_catbox(args.file)
            print(url)  # 标准输出只给 URL，便于脚本捕获
            print(f"[host={host}]", file=sys.stderr)
            return
        except Exception as exc:  # noqa: BLE001 - 回退需吞掉单端点错误
            last_err = exc
            print(f"{host} 上传失败: {exc}", file=sys.stderr)
    sys.exit(f"所有图床均上传失败: {last_err}")


if __name__ == "__main__":
    main()
