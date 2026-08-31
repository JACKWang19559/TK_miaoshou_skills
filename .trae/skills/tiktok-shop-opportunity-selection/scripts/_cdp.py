# -*- coding: utf-8 -*-
"""Chrome DevTools Protocol (CDP) 轻量客户端与 TikTok 登录态注入工具。

供本技能内其它脚本复用的共享模块，提供三类能力：
1. 通过 CDP HTTP 端点发现浏览器级 / 页面级 WebSocket 地址；
2. 把 EditThisCookie 格式的 cookie 文件注入受管浏览器（含 httpOnly 登录凭证）；
3. 同步 CDP 命令调用封装。

依赖：requests、websocket-client。运行前提：受管浏览器以
``--remote-debugging-port=<port>`` 启动（本技能默认端口 9222）。

安全提示：本模块只读取 cookie 文件并写入浏览器 cookie 存储，绝不打印
任何 cookie 值，也绝不把凭证写入磁盘或提交到版本库。
"""
import json

import requests
import websocket

# TikTok 卖家中心（跨境）域名与商品机会页路径
SELLER_HOST = "seller.tiktokshopglobalselling.com"
OPPORTUNITY_PATH = "/product/opportunity"

# lead/list 接口路径片段，用于网络监听匹配
LEAD_LIST_PATH = "/seller_product_opportunity/seller/lead/list"


class CDP:
    """封装 CDP WebSocket 连接与同步命令调用。

    Attributes:
        ws: websocket-client 连接实例。
    """

    def __init__(self, ws_url, timeout=30):
        """建立到指定 WebSocket 地址的 CDP 连接。

        Args:
            ws_url: CDP 目标（浏览器或页面）的 WebSocket 调试地址。
            timeout: recv 超时秒数。
        """
        # suppress_origin 避免发送 Origin 头，否则 Chrome CDP 会返回 403
        self.ws = websocket.create_connection(
            ws_url, timeout=timeout, suppress_origin=True,
        )
        self._seq = 0

    def call(self, method, params=None):
        """发送一条 CDP 命令并同步等待其响应。

        Args:
            method: CDP 方法名，例如 ``Page.navigate``。
            params: 方法参数，缺省为空字典。

        Returns:
            响应的 result 字段。

        Raises:
            RuntimeError: 当 CDP 返回 error 时。
        """
        self._seq += 1
        message = {"id": self._seq, "method": method, "params": params or {}}
        self.ws.send(json.dumps(message))
        while True:
            obj = json.loads(self.ws.recv())
            if obj.get("id") == self._seq:
                if "error" in obj:
                    raise RuntimeError(f"{method} 失败: {obj['error']}")
                return obj.get("result", {})

    def close(self):
        """关闭底层 WebSocket 连接。"""
        self.ws.close()


def browser_ws_url(port):
    """返回浏览器级 CDP WebSocket 地址。

    Args:
        port: CDP 调试端口。

    Returns:
        browser target 的 webSocketDebuggerUrl。
    """
    resp = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=5)
    return resp.json()["webSocketDebuggerUrl"]


def page_ws_url(port, host=SELLER_HOST):
    """返回指定域名的页面级 CDP WebSocket 地址。

    Args:
        port: CDP 调试端口。
        host: 要匹配的页面域名，缺省为卖家中心域名。

    Returns:
        匹配域名的 page target WebSocket 地址；找不到则回退到第一个 page target。
    """
    resp = requests.get(f"http://127.0.0.1:{port}/json", timeout=5)
    pages = [t for t in resp.json() if t.get("type") == "page"]
    for target in pages:
        if host in target.get("url", ""):
            return target["webSocketDebuggerUrl"]
    return pages[0]["webSocketDebuggerUrl"] if pages else None


def _map_samesite(value):
    """把 EditThisCookie 的 sameSite 取值映射为 CDP 枚举。

    Args:
        value: EditThisCookie 中的 sameSite 字符串。

    Returns:
        CDP 接受的 ``Strict``/``Lax``/``None``，无法映射时返回 None。
    """
    mapping = {"no_restriction": "None", "lax": "Lax", "strict": "Strict"}
    return mapping.get(value)


def inject_cookies(cookie_file, port):
    """把 EditThisCookie 格式的 cookie 文件注入浏览器。

    Args:
        cookie_file: cookie JSON 文件路径（含 ``cookies`` 数组）。
        port: CDP 调试端口。

    Returns:
        成功注入的 cookie 数量。
    """
    with open(cookie_file, encoding="utf-8") as fh:
        raw = json.load(fh)
    cookies = raw.get("cookies", [])

    cdp_cookies = []
    for item in cookies:
        entry = {
            "name": item["name"],
            "value": item["value"],
            # domain 保留原始前导点，确保父域 cookie 对子域生效
            "domain": item["domain"],
            "path": item.get("path", "/"),
        }
        if item.get("expirationDate"):
            entry["expires"] = item["expirationDate"]
        if item.get("httpOnly"):
            entry["httpOnly"] = True
        if item.get("secure"):
            entry["secure"] = True
        same_site = _map_samesite(item.get("sameSite"))
        if same_site:
            entry["sameSite"] = same_site
        cdp_cookies.append(entry)

    client = CDP(browser_ws_url(port))
    try:
        client.call("Storage.setCookies", {"cookies": cdp_cookies})
    finally:
        client.close()
    return len(cdp_cookies)
