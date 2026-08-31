#!/usr/bin/env python3
"""Read-only client for Miaoshou TikTok pricing settings and templates."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://openapi-erp.91miaoshou.com"
DEFAULTS_PATH = "/open/v1/product/collect_box/tiktok/price_template/get_site_default_setting"
TEMPLATES_PATH = "/open/v1/product/collect_box/tiktok/price_template/get_price_template_list"


def load_config(explicit: str | None) -> dict[str, Any]:
    candidates = [Path(explicit)] if explicit else []
    if os.getenv("MIAOSHOU_CONFIG_PATH"):
        candidates.append(Path(os.environ["MIAOSHOU_CONFIG_PATH"]))
    candidates.append(SKILL_DIR / "resources" / "config.json")
    config: dict[str, Any] = {}
    for path in candidates:
        if path.exists():
            config.update(json.loads(path.read_text(encoding="utf-8-sig")))
            break
    for env, key in (("MIAOSHOU_APP_KEY", "app_key"), ("MIAOSHOU_APP_SECRET", "app_secret"), ("MIAOSHOU_BASE_URL", "base_url")):
        if os.getenv(env):
            config[key] = os.environ[env]
    config.setdefault("base_url", DEFAULT_BASE_URL)
    return config


def post(config: dict[str, Any], path: str, payload: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in ("app_key", "app_secret") if not config.get(key)]
    if missing:
        raise RuntimeError(f"Missing Miaoshou config field(s): {', '.join(missing)}")
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    timestamp = str(int(time.time()))
    secret, app_key = str(config["app_secret"]), str(config["app_key"])
    signature = hmac.new(secret.encode(), f"{secret}{path}{timestamp}{app_key}{body}{secret}".encode(), hashlib.sha256).hexdigest()
    request = urllib.request.Request(str(config["base_url"]).rstrip("/") + path, data=body.encode("utf-8"), headers={"Content-Type": "application/json", "x-app-key": app_key, "x-timestamp": timestamp, "x-sign": signature}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc
    value["_retrievedAt"] = datetime.now(timezone.utc).isoformat()
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor")
    defaults = sub.add_parser("site-defaults")
    defaults.add_argument("--out")
    templates = sub.add_parser("templates")
    templates.add_argument("--site")
    templates.add_argument("--site-type", choices=("cross_border", "mainland"))
    templates.add_argument("--name")
    templates.add_argument("--page", type=int, default=1)
    templates.add_argument("--page-size", type=int, default=20)
    templates.add_argument("--out")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == "doctor":
        result = {"ready": bool(config.get("app_key") and config.get("app_secret")), "baseUrl": config["base_url"], "hasAppKey": bool(config.get("app_key")), "hasAppSecret": bool(config.get("app_secret"))}
    elif args.command == "site-defaults":
        result = post(config, DEFAULTS_PATH, {})
    else:
        if not 1 <= args.page_size <= 20 or args.page < 1:
            parser.error("page must be >=1 and page-size must be 1-20")
        payload = {"pageNo": args.page, "pageSize": args.page_size}
        for key, value in (("site", args.site), ("siteType", args.site_type), ("name", args.name)):
            if value:
                payload[key] = value
        result = post(config, TEMPLATES_PATH, payload)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    out = getattr(args, "out", None)
    if out:
        Path(out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
