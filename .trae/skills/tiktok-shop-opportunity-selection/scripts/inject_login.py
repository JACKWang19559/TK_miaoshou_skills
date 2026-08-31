# -*- coding: utf-8 -*-
"""注入 TikTok 卖家中心登录态并打开「商品机会」页。

用法：
    py inject_login.py --cookie-file <cookie.json> [--region VN] [--cdp-port 9222]

完成后浏览器会停在商品机会页，供后续 fetch_leads.py 抓取，或人工核验。
本脚本只写入 cookie 并导航，不打印、不外发任何凭证。
"""
import argparse
import time

from _cdp import CDP, page_ws_url, inject_cookies, SELLER_HOST


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="注入登录态并打开商品机会页")
    parser.add_argument("--cookie-file", required=True, help="EditThisCookie 格式的 cookie JSON 文件")
    parser.add_argument("--region", default="VN", help="目标站点，默认 VN")
    parser.add_argument("--cdp-port", type=int, default=9222, help="Chrome 调试端口，默认 9222")
    return parser.parse_args()


def main():
    """主流程：注入 cookie → 导航到商品机会页 → 等待渲染。"""
    args = parse_args()

    count = inject_cookies(args.cookie_file, args.cdp_port)
    print(f"已注入 {count} 个 cookie")

    url = f"https://{SELLER_HOST}/product/opportunity?shop_region={args.region}"
    page_ws = page_ws_url(args.cdp_port)
    if page_ws is None:
        raise SystemExit("未找到页面 target，请确认受管浏览器已启动并开启调试端口")

    client = CDP(page_ws)
    try:
        client.call("Page.enable")
        client.call("Page.navigate", {"url": url})
    finally:
        client.close()

    time.sleep(5)
    print(f"已打开商品机会页：{url}")
    print("请在浏览器中确认是否已登录成功（页面不再是登录页）")


if __name__ == "__main__":
    main()
