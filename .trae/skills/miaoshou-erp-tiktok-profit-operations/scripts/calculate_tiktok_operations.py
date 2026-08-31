#!/usr/bin/env python3
"""Normalize Miaoshou pricing configuration and calculate TikTok economics."""

from __future__ import annotations

import argparse
import ast
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


LEGACY_RATE_FIELDS = (
    "platform_fee_rate", "payment_fee_rate", "creator_commission_rate",
    "ad_cost_rate", "return_rate", "unrecoverable_return_fraction",
    "target_contribution_margin",
)

TEMPLATE_RATE_MAP = {
    "platformChargePercent": "platform_charge",
    "paymentChargePercent": "payment_charge",
    "activityChargePercent": "activity_charge",
    "withdrawChargePercent": "withdraw_charge",
}

DEFAULT_RATE_MAP = {
    "platformChargePercent": "platform_charge",
    "paymentChargePercent": "payment_charge",
    "withdrawChargePercent": "withdraw_charge",
    "sfpChargePercent": "sfp_charge",
    "affiliateChargePercent": "affiliate_charge",
    "vatChargePercent": "vat_charge",
    "tariffChargePercent": "tariff_charge",
    "freeShippingChargePercent": "free_shipping_charge",
    "eCommerceGrowthChargePercent": "ecommerce_growth_charge",
    "bcpChargePercent": "bcp_charge",
    "consumptionTaxChargePercent": "consumption_tax_charge",
    "localConsumptionTaxChargePercent": "local_consumption_tax_charge",
}


def number(data: Dict[str, Any], key: str, default: float = 0.0) -> float:
    value = data.get(key, default)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    value = float(value)
    if value < 0:
        raise ValueError(f"{key} must be nonnegative")
    return value


def money(value: float) -> float:
    return round(value + 0.0, 2)


def _response_data(value: Any) -> dict[str, Any]:
    return value.get("data", {}) if isinstance(value, dict) and isinstance(value.get("data"), dict) else value


def _percent(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{field} must be a nonnegative percentage")
    return float(value) / 100.0


def _select_template(raw: dict[str, Any], template_id: int | None) -> dict[str, Any]:
    data = _response_data(raw)
    items = data.get("priceTemplateList", []) if isinstance(data, dict) else []
    if not isinstance(items, list):
        raise ValueError("priceTemplateList must be an array")
    if template_id is not None:
        items = [item for item in items if str(item.get("priceTemplateId")) == str(template_id)]
    if len(items) != 1:
        raise ValueError(f"expected exactly one pricing template, found {len(items)}")
    return items[0]


def _weight_charge(template: dict[str, Any], weight: float | None) -> tuple[float | None, str | None]:
    mode = template.get("logisticsComputeType")
    if mode == "fixed":
        return number(template, "logisticsCharge"), None
    if mode == "first_continued":
        if weight is None:
            return None, "chargeable_weight"
        first_interval = number(template, "firstWeightInterval")
        continued_interval = number(template, "continuedWeightInterval")
        if first_interval <= 0 or continued_interval <= 0:
            return None, "valid_first_and_continued_weight_intervals"
        excess = max(0.0, weight - first_interval)
        return number(template, "firstWeightCharge") + math.ceil(excess / continued_interval) * number(template, "continuedWeightCharge"), None
    if mode == "weight_interval":
        if weight is None:
            return None, "chargeable_weight"
        raw_bands = template.get("weightLogisticsChargeList")
        try:
            bands = json.loads(raw_bands) if isinstance(raw_bands, str) else raw_bands
            if not isinstance(bands, list):
                raise ValueError
            for band in bands:
                low = float(band.get("minWeight", 0))
                high = float(band["maxWeight"])
                if low <= weight <= high:
                    return float(band["charge"]), None
        except (ValueError, TypeError, KeyError, json.JSONDecodeError, SyntaxError):
            try:
                bands = ast.literal_eval(raw_bands) if isinstance(raw_bands, str) else None
            except (ValueError, SyntaxError):
                bands = None
            if isinstance(bands, list):
                for band in bands:
                    if isinstance(band, dict) and float(band.get("minWeight", 0)) <= weight <= float(band["maxWeight"]):
                        return float(band["charge"]), None
        return None, "matching_weight_interval"
    if mode == "official_freight_tpl":
        return None, "resolved_official_freight_amount"
    return None, "supported_logistics_mode" if mode else None


def normalize_pricing_context(raw: dict[str, Any], source_type: str, site: str, template_id: int | None = None, chargeable_weight: float | None = None) -> dict[str, Any]:
    site = site.upper()
    context: dict[str, Any] = {
        "schema_version": "miaoshou-tiktok-pricing-context-v1",
        "source_type": source_type,
        "site": site,
        "retrieved_at": raw.get("_retrievedAt") or datetime.now(timezone.utc).isoformat(),
        "rate_components": {}, "amount_components": {}, "metadata": {},
        "ignored_fields": [], "missing_inputs": [],
    }
    if source_type == "template":
        item = _select_template(raw, template_id)
        if str(item.get("site", "")).upper() != site:
            raise ValueError("selected template site does not match requested site")
        context["currency"] = item.get("currency")
        context["metadata"] = {key: item.get(key) for key in (
            "priceTemplateId", "name", "site", "profitType", "profitPercent",
            "fixedProfitAmount", "exchangeRate", "discount", "logisticsComputeType",
            "weightRefType", "snapshotId", "gmtModified",
        )}
        for source, target in TEMPLATE_RATE_MAP.items():
            if item.get(source) is not None:
                context["rate_components"][target] = _percent(item[source], source)
        if item.get("otherCharge") is not None:
            context["amount_components"]["other_charge"] = number(item, "otherCharge")
        if item.get("hasSellerLogisticCharge") == 1 and item.get("sellerLogisticCharge") is not None:
            context["amount_components"]["seller_logistics_charge"] = number(item, "sellerLogisticCharge")
        logistics, missing = _weight_charge(item, chargeable_weight)
        if logistics is not None:
            context["amount_components"]["international_logistics_charge"] = logistics
        if missing:
            context["missing_inputs"].append(missing)
        domestic_mode = item.get("domesticLogisticsComputeType")
        if domestic_mode == "fixed" and item.get("domesticLogisticsCharge") is not None:
            context["amount_components"]["domestic_logistics_charge"] = number(item, "domesticLogisticsCharge")
        elif domestic_mode == "first_continued":
            context["missing_inputs"].append("domestic_chargeable_weight_or_resolved_domestic_logistics")
        context["metadata"]["buyerLogisticCharge"] = item.get("buyerLogisticCharge")
        context["ignored_fields"].extend(["profit target is metadata, not cost", "buyerLogisticCharge is not seller cost", "price rounding/tail/discount are not used in realized contribution"])
    elif source_type == "site_default":
        data = _response_data(raw)
        percentage_map = data.get("tiktokCbSiteAndDefaultChargePercentMap", {})
        site_rates = percentage_map.get(site) if isinstance(percentage_map, dict) else None
        if isinstance(site_rates, dict):
            for source, target in DEFAULT_RATE_MAP.items():
                if site_rates.get(source) is not None:
                    context["rate_components"][target] = _percent(site_rates[source], source)
        else:
            context["missing_inputs"].append("unambiguous_site_default_percentage_configuration")
        amount_maps = {
            "buyer_logistics_default": "siteAndBuyerLogisticDefaultChargeMap",
            "platform_infrastructure_charge": "siteAndDefaultPlatformInfrastructureChargeMap",
            "platform_support_charge": "siteAndDefaultPlatformSupportChargeMap",
        }
        for target, source in amount_maps.items():
            mapping = data.get(source, {})
            if isinstance(mapping, dict) and mapping.get(site) is not None:
                if target == "buyer_logistics_default":
                    context["metadata"][target] = mapping[site]
                    context["ignored_fields"].append("buyer logistics default is not automatically a seller cost")
                else:
                    context["amount_components"][target] = float(mapping[site])
        if data.get("tiktokLocalDefaultChargePercentMap"):
            context["ignored_fields"].append("tiktokLocalDefaultChargePercentMap requires an unambiguous live site mapping")
    else:
        raise ValueError("source_type must be template or site_default")
    context["missing_inputs"] = sorted(set(context["missing_inputs"]))
    return context


def calculate_unit(data: Dict[str, Any]) -> Dict[str, Any]:
    for key in LEGACY_RATE_FIELDS:
        if key in data and number(data, key) > 1:
            raise ValueError(f"{key} must be between 0 and 1")
    price = number(data, "selling_price")
    if price <= 0:
        raise ValueError("selling_price must be greater than 0")
    fixed_keys = ("product_cost", "inbound_shipping", "fulfillment_cost", "outbound_shipping", "packaging_cost", "other_fixed_cost")
    fixed = {key: number(data, key) for key in fixed_keys}
    context = data.get("pricing_context") or {}
    if not isinstance(context, dict):
        raise ValueError("pricing_context must be an object")
    rate_components = dict(context.get("rate_components") or {})
    amount_components = dict(context.get("amount_components") or {})
    legacy_rates = {
        "platform_charge": number(data, "platform_fee_rate"),
        "payment_charge": number(data, "payment_fee_rate"),
        "creator_commission": number(data, "creator_commission_rate"),
        "ad_cost": number(data, "ad_cost_rate"),
    }
    overrides = []
    for key, value in legacy_rates.items():
        source_key = {"platform_charge": "platform_fee_rate", "payment_charge": "payment_fee_rate", "creator_commission": "creator_commission_rate", "ad_cost": "ad_cost_rate"}[key]
        if source_key in data:
            if key in rate_components:
                overrides.append(key)
            rate_components[key] = value
    for key in ("platform_charge", "payment_charge", "creator_commission", "ad_cost"):
        rate_components.setdefault(key, 0.0)
    for key, value in rate_components.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"pricing rate {key} must be between 0 and 1")
    for key, value in amount_components.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"pricing amount {key} must be nonnegative")
    rate_costs = {f"{key}_cost": price * float(value) for key, value in rate_components.items()}
    return_rate = number(data, "return_rate")
    return_loss = return_rate * (number(data, "return_processing_cost") + number(data, "return_shipping_cost") + fixed["product_cost"] * number(data, "unrecoverable_return_fraction"))
    total_cost = sum(fixed.values()) + sum(float(v) for v in amount_components.values()) + sum(rate_costs.values()) + return_loss
    contribution = price - total_cost
    total_rate = sum(float(v) for v in rate_components.values())
    fixed_for_break_even = sum(fixed.values()) + sum(float(v) for v in amount_components.values()) + return_loss
    denominator = 1 - total_rate
    non_ad_cost = total_cost - rate_costs.get("ad_cost_cost", 0.0)
    result: Dict[str, Any] = {
        "schema_version": "miaoshou-tiktok-unit-economics-v2",
        "selling_price": money(price),
        "pricing_source": {key: context.get(key) for key in ("source_type", "site", "currency", "retrieved_at", "metadata") if context.get(key) is not None},
        "overridden_api_components": overrides,
        "costs": {**{k: money(v) for k, v in fixed.items()}, **{k: money(float(v)) for k, v in amount_components.items()}, **{k: money(v) for k, v in rate_costs.items()}},
        "expected_return_loss": money(return_loss),
        "total_variable_cost": money(total_cost),
        "contribution_profit": money(contribution),
        "contribution_margin": round(contribution / price, 4),
        "break_even_price": money(fixed_for_break_even / denominator) if denominator > 0 else None,
        "break_even_ad_cost_rate": round(max(0.0, (price - non_ad_cost) / price), 4),
        "source_missing_inputs": context.get("missing_inputs", []),
        "source_ignored_fields": context.get("ignored_fields", []),
    }
    if "target_contribution_margin" in data:
        target_denominator = denominator - number(data, "target_contribution_margin")
        result["target_price"] = money(fixed_for_break_even / target_denominator) if target_denominator > 0 else None
    return result


def calculate_price(data: Dict[str, Any]) -> Dict[str, Any]:
    context = data.get("pricing_context") or {}
    if not isinstance(context, dict):
        raise ValueError("pricing_context must be an object")
    rates = dict(context.get("rate_components") or {})
    for key, source_key in (("creator_commission", "creator_commission_rate"), ("ad_cost", "ad_cost_rate")):
        if source_key in data:
            rates[key] = number(data, source_key)
    for key, value in rates.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"pricing rate {key} must be between 0 and 1")
    amounts = dict(context.get("amount_components") or {})
    fixed_keys = ("product_cost", "inbound_shipping", "fulfillment_cost", "outbound_shipping", "packaging_cost", "other_fixed_cost")
    fixed = sum(number(data, key) for key in fixed_keys) + sum(float(v) for v in amounts.values())
    return_loss = number(data, "return_rate") * (number(data, "return_processing_cost") + number(data, "return_shipping_cost") + number(data, "product_cost") * number(data, "unrecoverable_return_fraction"))
    fixed += return_loss
    has_margin = "target_contribution_margin" in data
    has_amount = "target_profit_amount" in data
    if has_margin == has_amount:
        raise ValueError("provide exactly one of target_contribution_margin or target_profit_amount")
    total_rate = sum(float(v) for v in rates.values())
    if has_margin:
        target = number(data, "target_contribution_margin")
        if target > 1:
            raise ValueError("target_contribution_margin must be between 0 and 1")
        denominator = 1 - total_rate - target
        target_kind, target_value = "contribution_margin", target
        numerator = fixed
    else:
        denominator = 1 - total_rate
        target_kind, target_value = "profit_amount", number(data, "target_profit_amount")
        numerator = fixed + target_value
    candidate = numerator / denominator if denominator > 0 else None
    return {
        "schema_version": "miaoshou-tiktok-price-recommendation-v1",
        "pricing_source": {key: context.get(key) for key in ("source_type", "site", "currency", "retrieved_at", "metadata") if context.get(key) is not None},
        "target": {"type": target_kind, "value": target_value},
        "total_price_based_rate": round(total_rate, 6),
        "fixed_and_amount_cost": money(fixed),
        "candidate_price_before_rounding": money(candidate) if candidate is not None else None,
        "source_missing_inputs": context.get("missing_inputs", []),
        "unapplied_template_price_processing": ["exchangeRate", "discount", "priceTailComputeType", "priceTail", "priceProcessDecimalType"],
    }


def calculate_inventory(data: Dict[str, Any]) -> Dict[str, Any]:
    available = max(0.0, number(data, "on_hand") + number(data, "on_order") - number(data, "reserved"))
    daily = number(data, "daily_demand")
    lead, review, safety = number(data, "lead_time_days"), number(data, "review_period_days"), number(data, "safety_days")
    moq = number(data, "minimum_order_quantity")
    reorder_point, target_stock = daily * (lead + safety), daily * (lead + review + safety)
    raw_order = max(0.0, target_stock - available)
    suggested = math.ceil(raw_order / moq) * moq if moq > 0 and raw_order > 0 else raw_order
    return {"schema_version": "miaoshou-tiktok-inventory-scenario-v1", "available_stock": round(available, 2), "stock_cover_days": round(available / daily, 2) if daily > 0 else None, "reorder_point": round(reorder_point, 2), "target_stock": round(target_stock, 2), "suggested_order_quantity": round(suggested, 2), "estimated_order_cash": money(suggested * number(data, "unit_landed_cost")), "reorder_now": available <= reorder_point if daily > 0 else False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("pricing-context", "price", "unit", "inventory"))
    parser.add_argument("--input", required=True)
    parser.add_argument("--out")
    parser.add_argument("--source-type", choices=("template", "site_default"))
    parser.add_argument("--site")
    parser.add_argument("--template-id", type=int)
    parser.add_argument("--chargeable-weight", type=float)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    if args.mode == "pricing-context":
        if not args.source_type or not args.site:
            parser.error("pricing-context requires --source-type and --site")
        result = normalize_pricing_context(data, args.source_type, args.site, args.template_id, args.chargeable_weight)
    elif args.mode == "price":
        result = calculate_price(data)
    else:
        result = calculate_unit(data) if args.mode == "unit" else calculate_inventory(data)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
