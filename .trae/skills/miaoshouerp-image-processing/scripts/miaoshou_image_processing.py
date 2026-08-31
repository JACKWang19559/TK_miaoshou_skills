#!/usr/bin/env python3
"""Miaoshou ERP signed client and guarded CLI for image-processing APIs."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_BASE_URL = "https://openapi-erp.91miaoshou.com"

PATHS = {
    "remove": "/open/v1/product/common/image_removal/remove_image",
    "white-bg": "/open/v1/product/picture/matting/auto_ai_matting_multi",
    "search-watermarks": "/open/v1/product/item/tiktok/watermark/search_watermark_list",
    "watermark": "/open/v1/product/item/tiktok/watermark/watermark_images",
    "languages": "/open/v1/product/common/translate/get_support_language_config",
    "translate": "/open/v1/product/common/translate/translate_image",
}

PROCESSING_COMMANDS = {"remove", "white-bg", "watermark", "translate"}


class ConfigError(RuntimeError):
    """Raised when local OpenAPI configuration is missing or invalid."""


class ApiError(RuntimeError):
    """Raised when a request fails before a valid API payload is returned."""


@dataclass(frozen=True)
class MiaoshouConfig:
    app_key: str
    app_secret: str
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30
    account_id: str | None = None
    authorization: str | None = None
    cookie: str | None = None


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_config_path() -> Path:
    return skill_root() / "resources" / "config.json"


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.startswith("optional_") or text.startswith("your_"):
        return None
    return text


def load_config(config_path: str | os.PathLike[str] | None = None) -> MiaoshouConfig:
    raw: dict[str, Any] = {}
    path = Path(config_path) if config_path else default_config_path()
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Cannot read configuration: {exc}") from exc

    app_key = os.getenv("MIAOSHOU_APP_KEY") or str(raw.get("app_key", "")).strip()
    app_secret = os.getenv("MIAOSHOU_APP_SECRET") or str(raw.get("app_secret", "")).strip()
    base_url = os.getenv("MIAOSHOU_BASE_URL") or str(raw.get("base_url", DEFAULT_BASE_URL)).strip()
    timeout_raw = os.getenv("MIAOSHOU_TIMEOUT") or raw.get("timeout", 30)

    if not app_key or app_key == "your_app_key_here":
        raise ConfigError("Missing app_key. Set MIAOSHOU_APP_KEY or resources/config.json.")
    if not app_secret or app_secret == "your_app_secret_here":
        raise ConfigError("Missing app_secret. Set MIAOSHOU_APP_SECRET or resources/config.json.")
    if not base_url.startswith(("https://", "http://")):
        raise ConfigError("base_url must start with https:// or http://.")
    try:
        timeout = int(timeout_raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError("timeout must be an integer number of seconds.") from exc
    if timeout < 1:
        raise ConfigError("timeout must be at least 1 second.")

    return MiaoshouConfig(
        app_key=app_key,
        app_secret=app_secret,
        base_url=base_url.rstrip("/"),
        timeout=timeout,
        account_id=os.getenv("MIAOSHOU_ACCOUNT_ID") or optional_text(raw.get("account_id")),
        authorization=os.getenv("MIAOSHOU_AUTHORIZATION") or optional_text(raw.get("authorization")),
        cookie=os.getenv("MIAOSHOU_COOKIE") or optional_text(raw.get("cookie")),
    )


def compact_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def sign_headers(
    config: MiaoshouConfig,
    path: str,
    body_json: str,
    *,
    timestamp: str | None = None,
) -> dict[str, str]:
    timestamp = timestamp or str(int(time.time()))
    sign_content = (
        config.app_secret
        + path
        + timestamp
        + config.app_key
        + body_json
        + config.app_secret
    )
    signature = hmac.new(
        config.app_secret.encode("utf-8"),
        sign_content.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-app-key": config.app_key,
        "x-timestamp": timestamp,
        "x-sign": signature,
    }
    if config.account_id:
        headers["x-account-id"] = config.account_id
    if config.authorization:
        headers["authorization"] = config.authorization
    if config.cookie:
        headers["cookie"] = config.cookie
    return headers


def post_json(
    config: MiaoshouConfig,
    path: str,
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    body_json = compact_json(payload) if payload is not None else ""
    request = urllib.request.Request(
        url=config.base_url + path,
        data=body_json.encode("utf-8"),
        headers=sign_headers(config, path, body_json),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout) as response:
            response_text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        response_text = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"HTTP {exc.code}: {response_text}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"Network error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ApiError("Request timed out; do not automatically retry a processing call.") from exc

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ApiError("API returned a non-JSON response.") from exc
    if not isinstance(result, dict):
        raise ApiError("API returned a JSON value that is not an object.")
    return result


def print_json(value: Any, *, stream: Any = None) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2), file=stream or sys.stdout)


def positive_int(raw: str) -> int:
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def validate_image_urls(values: Sequence[str]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = raw.strip()
        parsed = urllib.parse.urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Image URL must be an absolute HTTP(S) URL: {raw}")
        if value not in seen:
            seen.add(value)
            urls.append(value)
    if not urls:
        raise ValueError("Provide at least one image URL.")
    return urls


def safe_filename_from_url(url: str, index: int, content_type: str | None = None) -> str:
    """Build a deterministic, filesystem-safe name for a derived image."""
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}:
        suffix = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
        }.get((content_type or "").split(";", 1)[0].lower(), ".jpg")
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"miaoshou-{index:02d}-{digest}{suffix}"


def derived_image_urls(response: Mapping[str, Any]) -> list[str]:
    """Extract successful derived URLs from all supported processing responses."""
    data = response.get("data")
    if not isinstance(data, Mapping):
        return []
    candidates: list[Mapping[str, Any]] = []
    for key in ("imgMattingList", "imageRemovalUrlResultList", "watermarkDetail", "translateImageUrlResultList"):
        items = data.get(key)
        if isinstance(items, Sequence) and not isinstance(items, (str, bytes)):
            candidates.extend(item for item in items if isinstance(item, Mapping))
    urls: list[str] = []
    for item in candidates:
        if str(item.get("result", "")).lower() != "success":
            continue
        value = item.get("newImageUrl") or item.get("watermarkImageUrl")
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            urls.append(value)
    return unique(urls)


def download_derived_images(
    urls: Sequence[str], output_dir: str | os.PathLike[str], *, timeout: int
) -> list[dict[str, Any]]:
    """Download derived images without overwriting existing files."""
    directory = Path(output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []
    for index, url in enumerate(urls, start=1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Codex-Miaoshou-Skill/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type")
                content = response.read()
            filename = safe_filename_from_url(url, index, content_type)
            target = directory / filename
            if target.exists():
                stem, suffix = target.stem, target.suffix
                serial = 2
                while target.exists():
                    target = directory / f"{stem}-{serial}{suffix}"
                    serial += 1
            target.write_bytes(content)
            artifacts.append({"url": url, "status": "saved", "path": str(target), "bytes": len(content)})
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            artifacts.append({"url": url, "status": "download_failed", "reason": str(exc)})
    return artifacts


def unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def build_remove_payload(args: argparse.Namespace) -> dict[str, Any]:
    targets = [
        args.remove_watermark,
        args.remove_logo,
        args.remove_text,
        args.remove_psoriasis,
    ]
    if not any(targets):
        raise ValueError("Select at least one removal target.")
    if args.source == "collect_box" and args.collect_box_detail_id is None:
        raise ValueError("--collect-box-detail-id is required for source collect_box.")
    if args.source == "common_collect_box" and args.common_collect_box_detail_id is None:
        raise ValueError("--common-collect-box-detail-id is required for source common_collect_box.")
    if (args.source.startswith("collect_box") or args.source.startswith("item")) and not args.platform:
        raise ValueError("--platform is required for platform collect-box and item sources.")

    trace: dict[str, Any] = {"imageRemovalSource": args.source}
    if args.collect_box_detail_id is not None:
        trace["collectBoxDetailId"] = args.collect_box_detail_id
    if args.common_collect_box_detail_id is not None:
        trace["commonCollectBoxDetailId"] = args.common_collect_box_detail_id
    if args.platform:
        trace["platform"] = args.platform

    return {
        "imageUrls": validate_image_urls(args.image_url),
        "traceInfo": trace,
        "removeConfig": {
            "isRemoveWatermark": int(args.remove_watermark),
            "isRemoveLogo": int(args.remove_logo),
            "isRemoveText": int(args.remove_text),
            "isRemovePsoriasis": int(args.remove_psoriasis),
            "removeAreas": unique(args.area),
        },
    }


def build_white_bg_payload(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "imgUrls": validate_image_urls(args.image_url),
        "imageScene": args.image_scene,
    }


def build_search_watermarks_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "watermarkSubType": args.subtype,
        "pageNo": args.page_no,
        "pageSize": args.page_size,
    }
    if args.watermark_id:
        payload["watermarkIds"] = ",".join(unique(args.watermark_id))
    if args.name:
        payload["watermarkName"] = args.name
    return payload


def build_watermark_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "imageUrls": validate_image_urls(args.image_url),
        "watermarkId": args.watermark_id,
        "isAutoMatchImageSize": args.auto_match_image_size,
    }
    if args.collect_box_detail_id is not None:
        payload["collectBoxDetailId"] = args.collect_box_detail_id
    return payload


def build_translate_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "imageUrls": validate_image_urls(args.image_url),
        "sourceLang": args.source_lang,
        "targetLang": args.target_lang,
        "translatePlatform": args.platform,
    }
    exclusions: list[str] = []
    if args.exclude_product_text:
        exclusions.append("textInTheProduct")
    if args.exclude_brand:
        exclusions.append("brand")
    if exclusions:
        payload["noTranslateImageTextOptions"] = exclusions
    return payload


def extract_language_config(response: Mapping[str, Any]) -> Mapping[str, Any]:
    data = response.get("data")
    if not isinstance(data, Mapping):
        raise ApiError("Language configuration response has no data object.")
    config = data.get("supportLanguageConfig")
    if not isinstance(config, Mapping):
        raise ApiError("Language configuration response has no supportLanguageConfig object.")
    return config


def validate_language_pair(
    support: Mapping[str, Any],
    platform: str,
    source: str,
    target: str,
) -> None:
    platform_config = support.get(platform)
    if not isinstance(platform_config, Mapping):
        available = ", ".join(sorted(str(key) for key in support)) or "none"
        raise ValueError(f"Unsupported translation platform {platform!r}. Available: {available}.")

    candidate_maps: list[Mapping[str, Any]] = [platform_config]
    candidate_maps.extend(
        value for value in platform_config.values() if isinstance(value, Mapping)
    )
    targets: set[str] = set()
    for candidate in candidate_maps:
        raw_targets = candidate.get(source)
        if isinstance(raw_targets, Sequence) and not isinstance(raw_targets, (str, bytes)):
            targets.update(str(value) for value in raw_targets)
    if target not in targets:
        available = ", ".join(sorted(targets)) or "none"
        raise ValueError(
            f"Unsupported language pair for {platform}: {source}->{target}. "
            f"Targets available for {source}: {available}."
        )


def preview(command: str, payload: Mapping[str, Any] | None, *, confirmation: bool) -> None:
    print_json(
        {
            "preview": True,
            "operation": command,
            "method": "POST",
            "path": PATHS[command],
            "payload": payload,
            "requiresConfirmation": confirmation,
            "approvalSummary": {
                "imageCount": len(payload.get("imgUrls", payload.get("imageUrls", [])))
                if payload
                else 0,
                "quotaConsuming": confirmation,
            },
            "nextStep": "Rerun the identical command with --confirm after user approval."
            if confirmation
            else "Remove --dry-run to perform this read-only request.",
        }
    )


def response_exit_code(response: Mapping[str, Any]) -> int:
    result = response.get("result")
    return 0 if result is None or str(result).lower() == "success" else 1


def add_connection_args(parser: argparse.ArgumentParser, *, confirm: bool = False) -> None:
    parser.add_argument("--config", help="Path to a local JSON configuration file")
    parser.add_argument("--dry-run", action="store_true", help="Print the request without sending it")
    if confirm:
        parser.add_argument("--confirm", action="store_true", help="Submit the quota-consuming operation")
        parser.add_argument(
            "--output-dir",
            help="After success, download derived images to this directory without overwriting files",
        )


def add_image_urls(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--image-url",
        action="append",
        required=True,
        help="Absolute HTTP(S) image URL; repeat for multiple images",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Miaoshou ERP guarded image-processing OpenAPI helper"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check-config", help="Validate local configuration without a network call")
    check.add_argument("--config", help="Path to a local JSON configuration file")

    remove = subparsers.add_parser("remove", help="Preview or submit AI smart removal")
    add_image_urls(remove)
    remove.add_argument(
        "--source",
        required=True,
        choices=[
            "collect_box",
            "collect_box_add",
            "common_collect_box",
            "common_collect_box_add",
            "item",
            "item_add",
        ],
    )
    remove.add_argument("--collect-box-detail-id", type=int)
    remove.add_argument("--common-collect-box-detail-id", type=int)
    remove.add_argument("--platform")
    remove.add_argument("--remove-watermark", action="store_true")
    remove.add_argument("--remove-logo", action="store_true")
    remove.add_argument("--remove-text", action="store_true")
    remove.add_argument("--remove-psoriasis", action="store_true")
    remove.add_argument(
        "--area",
        action="append",
        choices=["background", "subject"],
        required=True,
        help="Removal region; repeat to select both",
    )
    add_connection_args(remove, confirm=True)

    white_bg = subparsers.add_parser("white-bg", help="Preview or submit AI white-background processing")
    add_image_urls(white_bg)
    white_bg.add_argument("--image-scene", required=True, type=int, choices=range(1, 6))
    add_connection_args(white_bg, confirm=True)

    search = subparsers.add_parser("search-watermarks", help="Search TikTok watermark templates")
    search.add_argument("--watermark-id", action="append", help="Watermark ID; repeat for multiple IDs")
    search.add_argument("--name", help="Fuzzy watermark name")
    search.add_argument("--subtype", required=True, choices=["normal", "byLayer"])
    search.add_argument("--page-no", type=positive_int, default=1)
    search.add_argument("--page-size", type=positive_int, default=20)
    add_connection_args(search)

    watermark = subparsers.add_parser("watermark", help="Preview or submit watermark application")
    add_image_urls(watermark)
    watermark.add_argument("--watermark-id", required=True)
    watermark.add_argument("--collect-box-detail-id", type=int)
    size_group = watermark.add_mutually_exclusive_group(required=True)
    size_group.add_argument(
        "--auto-match-image-size",
        dest="auto_match_image_size",
        action="store_true",
        help="Adapt watermark proportionally to the source image",
    )
    size_group.add_argument(
        "--fixed-800",
        dest="auto_match_image_size",
        action="store_false",
        help="Disable auto matching and request the default 800x800 output",
    )
    add_connection_args(watermark, confirm=True)

    languages = subparsers.add_parser("languages", help="Get live image-translation language support")
    add_connection_args(languages)

    translate = subparsers.add_parser("translate", help="Preview or submit image-text translation")
    add_image_urls(translate)
    translate.add_argument("--source-lang", required=True)
    translate.add_argument("--target-lang", required=True)
    translate.add_argument("--platform", required=True)
    translate.add_argument("--exclude-product-text", action="store_true")
    translate.add_argument("--exclude-brand", action="store_true")
    translate.add_argument(
        "--skip-language-check",
        action="store_true",
        help="Skip live pair validation only when a current config was checked separately",
    )
    add_connection_args(translate, confirm=True)

    return parser


def build_payload(command: str, args: argparse.Namespace) -> Mapping[str, Any] | None:
    builders = {
        "remove": build_remove_payload,
        "white-bg": build_white_bg_payload,
        "search-watermarks": build_search_watermarks_payload,
        "watermark": build_watermark_payload,
        "translate": build_translate_payload,
    }
    if command == "languages":
        return None
    return builders[command](args)


def run(args: argparse.Namespace) -> int:
    if args.command == "check-config":
        config = load_config(args.config)
        print_json(
            {
                "configured": True,
                "baseUrl": config.base_url,
                "timeout": config.timeout,
                "accountContext": {
                    "accountId": bool(config.account_id),
                    "authorization": bool(config.authorization),
                    "cookie": bool(config.cookie),
                },
                "secretsPrinted": False,
            }
        )
        return 0

    payload = build_payload(args.command, args)
    needs_confirmation = args.command in PROCESSING_COMMANDS
    confirmed = getattr(args, "confirm", False)
    if args.dry_run or (needs_confirmation and not confirmed):
        preview(args.command, payload, confirmation=needs_confirmation)
        return 0

    config = load_config(args.config)
    if args.command == "translate" and not args.skip_language_check:
        language_response = post_json(config, PATHS["languages"], None)
        if response_exit_code(language_response):
            print_json(language_response)
            return 1
        validate_language_pair(
            extract_language_config(language_response),
            args.platform,
            args.source_lang,
            args.target_lang,
        )

    response = post_json(config, PATHS[args.command], payload)
    if getattr(args, "output_dir", None):
        response["localArtifacts"] = download_derived_images(
            derived_image_urls(response), args.output_dir, timeout=config.timeout
        )
    print_json(response)
    return response_exit_code(response)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except (ConfigError, ApiError, ValueError) as exc:
        print_json({"result": "fail", "reason": str(exc)}, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
