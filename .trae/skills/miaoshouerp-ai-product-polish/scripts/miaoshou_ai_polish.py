#!/usr/bin/env python3
"""Preview and call Miaoshou ERP AI product-polish endpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://openapi-erp.91miaoshou.com"
SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SKILL_DIR / "resources" / "config.json"

PATHS = {
    "ai-names": "/open/v1/product/common/open_ai/get_generate_product_info_support_ai_name_list",
    "languages": "/open/v1/product/common/open_ai/get_language_name_code_map",
    "product-info": "/open/v1/product/common/open_ai/generate_product_info",
    "sku-spec": "/open/v1/product/common/open_ai/generate_sku_spec_name",
}

FUNCTION_MODULES = {"createCollectBox", "editCollectBox", "createItem", "editItem"}
EDIT_MODULES = {"editCollectBox", "editItem"}
PRODUCT_FIELDS = {
    "generateTypeList", "functionModule", "functionModuleProductId", "platform",
    "aiName", "title", "originalContent", "titleLengthLimit", "languageName",
    "keywordsList", "negativeWordsList", "categoryName", "site", "cid",
    "imageInfoList",
}
SKU_FIELDS = {
    "platform", "title", "aiName", "languageName", "functionModule",
    "skuPropertyList", "productId",
}


class InputError(ValueError):
    """Raised for locally invalid request payloads."""


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def read_json_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise InputError(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError(f"JSON in {path} must be an object")
    return value


def parse_payload(args: argparse.Namespace) -> dict[str, Any]:
    if bool(args.input) == bool(args.payload):
        raise InputError("Provide exactly one of --input or --payload")
    if args.input:
        return read_json_file(Path(args.input))
    try:
        value = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        raise InputError(f"Invalid JSON for --payload: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError("--payload must be a JSON object")
    return value


def require_fields(payload: dict[str, Any], fields: set[str]) -> None:
    missing = sorted(key for key in fields if key not in payload or payload[key] in (None, ""))
    if missing:
        raise InputError(f"Missing required field(s): {', '.join(missing)}")


def reject_unknown_fields(payload: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise InputError(f"Unsupported field(s): {', '.join(unknown)}")


def validate_string_list(payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if value is not None and (
        not isinstance(value, list) or any(not isinstance(item, str) for item in value)
    ):
        raise InputError(f"{field} must be an array of strings")


def validate_product_info(payload: dict[str, Any]) -> None:
    reject_unknown_fields(payload, PRODUCT_FIELDS)
    require_fields(
        payload,
        {"generateTypeList", "functionModule", "platform", "aiName", "title", "languageName"},
    )
    types = payload["generateTypeList"]
    if not isinstance(types, list) or not types or any(item not in {"title", "notes"} for item in types):
        raise InputError("generateTypeList must be a non-empty array containing only title and/or notes")
    if len(types) != len(set(types)):
        raise InputError("generateTypeList must not contain duplicates")
    module = payload["functionModule"]
    if module not in FUNCTION_MODULES:
        raise InputError(f"functionModule must be one of: {', '.join(sorted(FUNCTION_MODULES))}")
    if module in EDIT_MODULES and not payload.get("functionModuleProductId"):
        raise InputError("functionModuleProductId is required for editCollectBox/editItem")
    if "titleLengthLimit" in payload and (
        isinstance(payload["titleLengthLimit"], bool)
        or not isinstance(payload["titleLengthLimit"], int)
        or payload["titleLengthLimit"] <= 0
    ):
        raise InputError("titleLengthLimit must be a positive integer")
    for field in ("keywordsList", "negativeWordsList"):
        validate_string_list(payload, field)
    images = payload.get("imageInfoList")
    if images is not None:
        if not isinstance(images, list):
            raise InputError("imageInfoList must be an array")
        for index, item in enumerate(images):
            if not isinstance(item, dict) or not item.get("imageUrl"):
                raise InputError(f"imageInfoList[{index}].imageUrl is required")
            unknown = set(item) - {"imageUrl", "imageSource"}
            if unknown:
                raise InputError(f"imageInfoList[{index}] has unsupported field(s): {', '.join(sorted(unknown))}")
            if item.get("imageSource") not in (None, "productImage", "otherImage"):
                raise InputError(f"imageInfoList[{index}].imageSource must be productImage or otherImage")


def validate_sku_value(value: Any, path: str) -> None:
    if not isinstance(value, dict):
        raise InputError(f"{path} must be an object")
    unknown = set(value) - {"attrValueId", "attrValue", "imgUrl", "supplementarySkuImageUrls"}
    if unknown:
        raise InputError(f"{path} has unsupported field(s): {', '.join(sorted(unknown))}")
    if "attrValue" not in value:
        raise InputError(f"{path}.attrValue is required")
    images = value.get("supplementarySkuImageUrls")
    if images is not None and (
        not isinstance(images, list) or any(not isinstance(item, str) for item in images)
    ):
        raise InputError(f"{path}.supplementarySkuImageUrls must be an array of strings")


def validate_sku_spec(payload: dict[str, Any]) -> None:
    reject_unknown_fields(payload, SKU_FIELDS)
    require_fields(payload, {"platform", "aiName", "functionModule", "skuPropertyList"})
    if payload["platform"] != "tiktok":
        raise InputError("The supplied API document currently supports only platform=tiktok")
    if payload["aiName"] != "douBao1.6":
        raise InputError("The supplied SKU API document currently supports only aiName=douBao1.6")
    module = payload["functionModule"]
    if module not in FUNCTION_MODULES:
        raise InputError(f"functionModule must be one of: {', '.join(sorted(FUNCTION_MODULES))}")
    if module in EDIT_MODULES and not payload.get("productId"):
        raise InputError("productId is required for editCollectBox/editItem")
    properties = payload["skuPropertyList"]
    if not isinstance(properties, list) or not properties:
        raise InputError("skuPropertyList must be a non-empty array")
    for index, prop in enumerate(properties):
        path = f"skuPropertyList[{index}]"
        if not isinstance(prop, dict):
            raise InputError(f"{path} must be an object")
        unknown = set(prop) - {"attrName", "attrId", "attrValueList"}
        if unknown:
            raise InputError(f"{path} has unsupported field(s): {', '.join(sorted(unknown))}")
        if "attrName" not in prop or not isinstance(prop.get("attrValueList"), list) or not prop["attrValueList"]:
            raise InputError(f"{path} requires attrName and a non-empty attrValueList")
        for value_index, value in enumerate(prop["attrValueList"]):
            validate_sku_value(value, f"{path}.attrValueList[{value_index}]")


def load_runtime(args: argparse.Namespace) -> dict[str, Any]:
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG
    config: dict[str, Any] = {}
    if config_path.exists():
        config = read_json_file(config_path)
    timeout_raw = args.timeout or os.environ.get("MIAOSHOU_AI_TIMEOUT") or config.get("timeout", 60)
    try:
        timeout = int(timeout_raw)
    except (TypeError, ValueError) as exc:
        raise InputError("timeout must be an integer") from exc
    if timeout <= 0:
        raise InputError("timeout must be positive")
    return {
        "base_url": (args.base_url or os.environ.get("MIAOSHOU_AI_BASE_URL") or config.get("base_url") or DEFAULT_BASE_URL).rstrip("/"),
        "cookie": os.environ.get("MIAOSHOU_COOKIE") or config.get("cookie") or "",
        "timer_token": os.environ.get("MIAOSHOU_TIMER_TOKEN") or config.get("timer_token") or "",
        "timeout": timeout,
    }


def call_api(command: str, payload: dict[str, Any], args: argparse.Namespace) -> None:
    path = PATHS[command]
    if not args.execute:
        emit({"mode": "preview", "method": "POST", "path": path, "payload": payload})
        return
    runtime = load_runtime(args)
    query = urllib.parse.urlencode({"timerToken": runtime["timer_token"]}) if runtime["timer_token"] else ""
    url = runtime["base_url"] + path + (f"?{query}" if query else "")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if runtime["cookie"]:
        headers["Cookie"] = runtime["cookie"]
    if args.apifox_debug:
        headers["X-Apifox-Debug"] = "1"
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=runtime["timeout"]) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed: {exc.reason}") from exc
    try:
        emit(json.loads(raw))
    except json.JSONDecodeError:
        emit({"raw": raw})


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--execute", action="store_true", help="Send the live request; default is preview")
    parser.add_argument("--config", help="Path to a local JSON config file")
    parser.add_argument("--base-url", help="Override the API base URL")
    parser.add_argument("--timeout", type=int, help="Request timeout in seconds")
    parser.add_argument("--apifox-debug", action="store_true", help="Send X-Apifox-Debug: 1 in an authorized test environment")


def add_payload_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", help="Path to a UTF-8 JSON object")
    parser.add_argument("--payload", help="Inline JSON object")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Miaoshou ERP AI product title, description, and SKU polish helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("ai-names", "Get supported AI names"),
        ("languages", "Get supported target languages"),
        ("product-info", "Generate or polish title and description"),
        ("sku-spec", "Polish TikTok SKU sales specifications"),
    ):
        subparser = subparsers.add_parser(command, help=help_text)
        if command in {"product-info", "sku-spec"}:
            add_payload_args(subparser)
        add_common_args(subparser)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        payload: dict[str, Any] = {}
        if args.command in {"product-info", "sku-spec"}:
            payload = parse_payload(args)
            if args.command == "product-info":
                validate_product_info(payload)
            else:
                validate_sku_spec(payload)
        call_api(args.command, payload, args)
    except InputError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()

