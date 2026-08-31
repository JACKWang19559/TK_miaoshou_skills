# Miaoshou TikTok Pricing API Contract

## Read-only endpoints

- Site defaults: `POST /open/v1/product/collect_box/tiktok/price_template/get_site_default_setting` with `{}`.
- Pricing templates: `POST /open/v1/product/collect_box/tiktok/price_template/get_price_template_list` with `pageNo`, `pageSize` (1-20), and optional `name`, `site`, `siteType` (`cross_border` or `mainland`).

Use signed Miaoshou OpenAPI authentication. Never expose credentials or signed headers. Record retrieval time because configuration may change.

## Source selection

1. Use the exact saved template selected by the user when requested.
2. Otherwise use the exact site's current default configuration.
3. Use user-supplied components only for values absent from the API or explicit scenario overrides.
4. Keep overrides visible; never overwrite the raw API snapshot.

If multiple templates match, show `priceTemplateId`, `name`, `site`, `currency`, `profitType`, `profitPercent`/`fixedProfitAmount`, `logisticsComputeType`, `snapshotId`, and `gmtModified`. Do not guess which template applies.

## Normalized cost mapping

Percentage values returned as percentages must be divided by 100 before arithmetic.

Saved template percentage costs:

- `platformChargePercent` -> platform charge
- `paymentChargePercent` -> payment charge
- `activityChargePercent` -> activity charge
- `withdrawChargePercent` -> withdrawal charge

Saved template fixed costs:

- `otherCharge` -> other charge
- `buyerLogisticCharge` -> revenue offset/amount paid by buyer; do not treat it as seller cost
- `sellerLogisticCharge` -> seller logistics cost only when `hasSellerLogisticCharge=1`
- international logistics according to `logisticsComputeType`
- domestic logistics according to `domesticLogisticsComputeType`

Site-default cross-border percentages may include platform, payment, withdrawal, SFP, affiliate, VAT, tariff, free-shipping, ecommerce-growth, BCP, consumption-tax, and local-consumption-tax charges. Map only fields present for the exact site.

Site-default fixed amounts may include buyer logistics, infrastructure, and platform-support amounts in site currency or CNY. Select one currency representation; never add both.

`tiktokLocalDefaultChargePercentMap` is not sufficiently described as a per-site structured object in the supplied contract. Preserve it as unparsed unless the live response makes the site/value relationship unambiguous.

## Logistics

- `fixed`: use `logisticsCharge`.
- `first_continued`: require chargeable weight and use the documented first/continued intervals and charges.
- `weight_interval`: parse `weightLogisticsChargeList` only when it is valid JSON or an unambiguous exported structure; select the matching interval.
- `official_freight_tpl`: report the mode/channel but do not invent a charge; require a resolved amount from current platform/template output or the user.
- Chargeable weight follows `weightRefType`: actual, volume, or maximum. When `isCalLightCargo=1`, require dimensions and use the documented coefficient only after confirming units.

Do not claim exact Miaoshou suggested-price parity from these endpoint schemas alone. The supplied API documents expose fields but not the complete ordering of discount, target profit, exchange rate, rounding, price-tail, and every logistics step.

## Profit target versus realized profit

`profitType`, `profitPercent`, and `fixedProfitAmount` describe the template's pricing target. Preserve them as metadata. Realized contribution uses actual selling price and applied costs; never add template target profit as an expense.

## Provenance output

Every normalized context must include source type, site, currency, retrieval time, template identity/snapshot when applicable, raw relevant fields, applied components, ignored fields with reasons, missing inputs, and explicit overrides.
