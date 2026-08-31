# -*- coding: utf-8 -*-
"""抓取 TikTok 卖家中心「商品机会」数据并落盘 JSON。

原理：商品机会接口（seller/lead/list）带 X-Bogus / X-Gnarly 反爬签名，
签名由页面 JS 动态生成，无法离线重放。因此本脚本让页面在真实浏览器里
自己发请求、自己算签名，通过 CDP 监听网络并捕获接口响应体。

支持在抓取前：
1. 筛选卖家可做的类目（--categories，逗号分隔类目 ID，如 ``601152``）；
2. 切换二级子筛选（--subtab trend = 「基于市场趋势的热门商品」，走 URL 参数）。

用法：
    py fetch_leads.py --cookie-file <cookie.json> --region VN \
        --categories 601152 --subtab trend --out opportunity_leads.json
"""
import argparse
import json
import time

import websocket

from _cdp import inject_cookies, page_ws_url, SELLER_HOST, OPPORTUNITY_PATH, LEAD_LIST_PATH

# 页面 UI 操作的 JavaScript 片段
JS_OPEN_FILTER = (
    "(function(){var b=[].slice.call(document.querySelectorAll('button'))"
    ".find(function(x){return x.textContent.trim()==='筛选';});"
    "if(b){b.click();return true;}return false;})()"
)
JS_CLICK_CATEGORY_INPUT = (
    "(function(){var i=document.querySelector('.core-drawer .core-input-tag-input');"
    "if(i){i.click();i.focus();return true;}return false;})()"
)
JS_CONFIRM_FILTER = (
    "(function(){var b=[].slice.call(document.querySelectorAll('button'))"
    ".find(function(x){return x.textContent.trim()==='确认';});"
    "if(b){b.click();return true;}return false;})()"
)
JS_CB_COUNT = "document.querySelectorAll('.core-cascader-popup input[type=checkbox]').length"
JS_FILTER_BTN_EXISTS = (
    "[].slice.call(document.querySelectorAll('button'))"
    ".some(function(x){return x.textContent.trim()==='筛选';})"
)
JS_SCROLL_BOTTOM = (
    "(function(){var els=[].slice.call(document.querySelectorAll('*')).filter("
    "function(e){return getComputedStyle(e).overflowY==='auto'"
    "&&e.scrollHeight>e.clientHeight+50;});"
    "els.sort(function(a,b){return b.scrollHeight-a.scrollHeight;});"
    "var el=els[0];"
    "if(el){for(var i=1;i<=6;i++){(function(i){setTimeout(function(){"
    "var t=el.scrollHeight;"
    "el.scrollTop=Math.max(0,t-el.clientHeight-2);"
    "el.dispatchEvent(new Event('scroll',{bubbles:true}));"
    "el.scrollTop=t;"
    "el.dispatchEvent(new Event('scroll',{bubbles:true}));"
    "},i*350);})(i);}"
    "return true;}return false;})()"
)


def _check_category_js(cate_id):
    """返回勾选指定类目 checkbox 的 JS 表达式（按 value 匹配）。"""
    return (
        "(function(){var cb=document.querySelector("
        "'.core-cascader-popup input[type=checkbox][value=\"" + str(cate_id) + "\"]');"
        "if(cb){cb.click();return true;}return false;})()"
    )


class LeadCollector:
    """通过 CDP 监听网络收集 lead/list 响应，并提供同步 eval 辅助 UI 操作。"""

    def __init__(self, ws):
        """初始化收集器。

        Args:
            ws: 已建立连接的页面级 WebSocket。
        """
        self.ws = ws
        self._seq = 0
        self.leads = {}
        self.total = None
        self._pending_body = {}

    def send(self, method, params=None):
        """发送一条 CDP 命令并返回命令 id。"""
        self._seq += 1
        self.ws.send(json.dumps({
            "id": self._seq, "method": method, "params": params or {},
        }))
        return self._seq

    def _recv_once(self):
        """读取一条消息；事件交给 on_message，命令响应原样返回。"""
        try:
            data = self.ws.recv()
        except websocket.WebSocketTimeoutException:
            return None
        obj = json.loads(data)
        if "method" in obj:
            self.on_message(obj)
            return None
        return obj

    def eval_js_sync(self, expression, timeout=10):
        """同步执行 JS 并返回 result.value。"""
        cmd_id = self.send("Runtime.evaluate", {
            "expression": expression, "returnByValue": True,
        })
        deadline = time.time() + timeout
        while time.time() < deadline:
            obj = self._recv_once()
            if obj is not None and obj.get("id") == cmd_id:
                return obj.get("result", {}).get("result", {}).get("value")
        return None

    def wait_until_true(self, expression, timeout=10, interval=0.5):
        """轮询等待 JS 表达式为真，返回是否成功。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.eval_js_sync(expression, timeout=3):
                return True
            time.sleep(interval)
        return False

    def reset(self):
        """清空已收集数据（用于筛选/切 tab 后重新抓取）。"""
        self.leads = {}
        self.total = None
        self._pending_body = {}

    def on_message(self, obj):
        """处理一条 CDP 消息（事件或命令响应）。"""
        method = obj.get("method")
        if method == "Network.responseReceived":
            resp = obj["params"]["response"]
            if LEAD_LIST_PATH in resp["url"] and resp["status"] == 200:
                request_id = obj["params"]["requestId"]
                cmd_id = self.send("Network.getResponseBody", {"requestId": request_id})
                self._pending_body[cmd_id] = request_id
        elif "id" in obj and obj["id"] in self._pending_body:
            body = obj.get("result", {}).get("body", "")
            self._consume(body)
            del self._pending_body[obj["id"]]

    def _consume(self, body):
        """解析 lead/list 响应体，合并去重。"""
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return
        total = data.get("total_product_count")
        if total:
            self.total = total
        for lead in data.get("data", []):
            self.leads[lead["lead_id"]] = lead


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="抓取 TikTok 商品机会数据")
    parser.add_argument("--cookie-file", required=True, help="EditThisCookie 格式的 cookie JSON 文件")
    parser.add_argument("--region", default="VN", help="目标站点，默认 VN")
    parser.add_argument("--out", default="opportunity_leads.json", help="输出 JSON 文件路径")
    parser.add_argument("--cdp-port", type=int, default=9222, help="Chrome 调试端口，默认 9222")
    parser.add_argument("--timeout", type=int, default=180, help="最长抓取秒数，默认 180")
    parser.add_argument("--stall-seconds", type=int, default=45, help="无新增数据的停滞判定秒数，默认 45")
    parser.add_argument("--categories", default=None,
                        help="要筛选的类目 ID（逗号分隔，如 601152）；不填则不过滤")
    parser.add_argument("--subtab", default="all", choices=["all", "trend"],
                        help="二级子筛选：all=全部, trend=基于市场趋势的热门商品")
    return parser.parse_args()


def main():
    """主流程：注入 cookie → 导航 → 筛选类目/切子 tab → 滚动翻页 → 落盘。"""
    args = parse_args()

    inject_cookies(args.cookie_file, args.cdp_port)

    ws_url = page_ws_url(args.cdp_port)
    if ws_url is None:
        raise SystemExit("未找到页面 target，请确认受管浏览器已启动")

    ws = websocket.create_connection(ws_url, timeout=0.3, suppress_origin=True)
    collector = LeadCollector(ws)
    collector.send("Network.enable")
    collector.send("Page.enable")
    collector.send("Runtime.enable")

    # 二级子筛选直接走 URL 参数，比 UI 点击更可靠
    query = f"shop_region={args.region}"
    if args.subtab == "trend":
        query += "&sub_tabs=shp_top_products"
    url = f"https://{SELLER_HOST}{OPPORTUNITY_PATH}?{query}"

    collector.send("Page.navigate", {"url": "about:blank"})
    time.sleep(1)
    collector.send("Page.navigate", {"url": url})
    time.sleep(3)

    # 筛选类目（卖家可做的类目）
    if args.categories:
        if not collector.wait_until_true(JS_FILTER_BTN_EXISTS, timeout=10):
            print("警告：未找到「筛选」按钮，跳过类目筛选")
        else:
            collector.eval_js_sync(JS_OPEN_FILTER)
            time.sleep(1)
            collector.eval_js_sync(JS_CLICK_CATEGORY_INPUT)
            if not collector.wait_until_true(JS_CB_COUNT + ">0", timeout=8):
                print("警告：级联类目未展开，跳过类目筛选")
            else:
                for cate_id in args.categories.split(","):
                    ok = collector.eval_js_sync(_check_category_js(cate_id.strip()))
                    print(f"勾选类目 {cate_id}: {ok}")
                    time.sleep(0.4)
                collector.eval_js_sync(JS_CONFIRM_FILTER)
                time.sleep(2)
                collector.reset()

    deadline = time.time() + args.timeout
    last_scroll = 0.0
    last_new = time.time()
    prev_count = 0

    while time.time() < deadline:
        try:
            data = ws.recv()
            collector.on_message(json.loads(data))
        except websocket.WebSocketTimeoutException:
            pass

        now = time.time()
        if len(collector.leads) > prev_count:
            last_new = now
            prev_count = len(collector.leads)

        if collector.total and len(collector.leads) >= collector.total:
            break
        if now - last_new > args.stall_seconds:
            break
        if (now - last_scroll > 2 and collector.total
                and len(collector.leads) < collector.total):
            collector.send("Runtime.evaluate", {"expression": JS_SCROLL_BOTTOM})
            last_scroll = now

    ws.close()

    result = {
        "region": args.region,
        "subtab": args.subtab,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_product_count": collector.total,
        "lead_count": len(collector.leads),
        "leads": list(collector.leads.values()),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print(f"已抓取 {len(collector.leads)} 条商机线索（平台总数 {collector.total}），写入 {args.out}")


if __name__ == "__main__":
    main()
