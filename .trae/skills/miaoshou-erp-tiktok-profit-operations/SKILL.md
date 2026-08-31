---
name: miaoshou-erp-tiktok-profit-operations
description: Price TikTok Shop products and analyze unit economics and operating risk for Miaoshou ERP users using current Miaoshou site-default settings or saved pricing templates when available. Use for 帮我定价、这个产品卖多少钱、TK利润计算、妙手定价模板、站点默认费率、定价底线、达人佣金、广告承受能力、物流成本、库存周转、补货和经营风险分析。Handle vague pricing requests by discovering the target site and dynamically requesting only inputs missing from the applicable template. Read-only only; never change templates, prices, inventory, fulfillment, or orders.
---

# Miaoshou ERP TikTok Profit Operations

Use Miaoshou pricing configuration as the preferred cost-structure source, then combine it with product-specific cost, price, weight, advertising, returns, inventory, and fulfillment evidence. Never replace available API configuration with embedded fee defaults.

## Workflow

1. Interpret vague requests such as “帮我定价” as a pricing task. Do not ask the user to name an API, pricing template, fee structure, or calculation formula.
2. Read `references/pricing-intake.md`. First establish only the routing inputs needed before API lookup: target TikTok site, seller/site type when ambiguous, product/SKU identity, and whether the user wants a new selling-price recommendation or profit evaluation of a known price. Ask site first when it is missing because fee, currency, logistics, tax, and template availability are site-dependent.
3. Query saved Miaoshou pricing templates for the exact site and optional site type. If exactly one relevant template exists, present it as the proposed source. If several exist, show a compact choice list and ask the user to select; do not expect them to know template IDs. If none exists or the user declines templates, fetch the exact site's default configuration.
4. Read `references/pricing-api-contract.md`. Normalize the selected API response with `scripts/calculate_tiktok_operations.py pricing-context`; preserve the raw source, retrieval time, template ID/snapshot, and every applied or ignored field.
5. Inspect the selected template before asking for costs. Build one dynamic question batch containing only unresolved product-specific inputs. Always resolve API-known platform fees, payment fees, template logistics rules, currency, exchange rate, discount settings, and target-profit settings before asking the user.
6. Acquire actual sales, product, order, inventory, and realized-profit evidence through `miaoshou-data-analysis` when available. Do not ask the user for values already available in trusted Miaoshou data.
7. For a new-price request, calculate and compare candidate selling-price scenarios using resolved template costs plus an explicit target contribution/profit guardrail. Treat Miaoshou template target profit as a starting target, not a realized-profit fact. For a known-price request, calculate contribution and break-even thresholds.
8. Run `scripts/calculate_tiktok_operations.py unit` with the normalized pricing context. Use `inventory` for reorder and stock-cover scenarios. Never silently substitute a missing API field with a fee default.
9. Compare a base case and the most decision-relevant downside case. Diagnose the binding constraint and return assumptions, formulas, results, sensitivity, confidence, and action thresholds separately.

## Script Usage

```powershell
python scripts/tiktok_pricing_api.py doctor
python scripts/tiktok_pricing_api.py site-defaults --out site-defaults.json
python scripts/tiktok_pricing_api.py templates --site US --page 1 --page-size 20 --out templates.json
python scripts/calculate_tiktok_operations.py pricing-context --input pricing-source.json --source-type template --site US --template-id 123 --out pricing-context.json
python scripts/calculate_tiktok_operations.py price --input price-input.json --out price-result.json
python scripts/calculate_tiktok_operations.py unit --input unit-input.json --out unit-result.json
python scripts/calculate_tiktok_operations.py inventory --input inventory-input.json --out inventory-result.json
```

`tiktok_pricing_api.py` performs signed read-only API calls. Use `price` to derive a pre-rounding candidate price from an explicit target contribution margin or amount, and `unit` to evaluate a known price. The calculator performs normalization and arithmetic only; it never fetches data or changes external state.

## Output Contract

Return exact scope and currency; pricing source (`template`, `site_default`, `user`, or mixed override); template ID/name/snapshot and modified time when applicable; API retrieval time; applied, overridden, ignored, and missing fields; assumptions requiring confirmation; dynamic cost breakdown; contribution and margin; break-even outputs when possible; sensitivity; inventory outputs when requested; and decision thresholds.

## Hard Rules

- Prefer a current saved template when the user requests it; do not recreate that template from remembered rates.
- Do not begin a vague pricing conversation with a fixed accounting questionnaire. Query the site/template first, then ask only for unresolved inputs.
- Do not ask the user to supply platform fee components that the current site configuration or selected template can provide.
- Do not silently select among multiple materially different templates. Show human-readable names and relevant differences instead of IDs alone.
- Do not interpret `profitPercent` or `fixedProfitAmount` as a cost. They are template pricing targets and must be reported separately from realized contribution.
- Do not claim exact parity with Miaoshou's displayed suggested price unless the documented rounding, logistics, discount, currency-conversion, and price-tail behavior has been reproduced and verified.
- Do not silently combine gross and tax-inclusive values, order and item grain, or different currencies.
- Do not treat GMV as revenue or contribution profit.
- Do not count return loss twice; use the model contract.
- Do not modify price, promotion, inventory, purchase order, fulfillment, or return state.
- Keep 1688 sourcing outside this Skill.

## References

- API fields and normalization: `references/pricing-api-contract.md`
- Conversational intake and dynamic questions: `references/pricing-intake.md`
- Inputs and formulas: `references/unit-economics-contract.md`
- Scenario interpretation: `references/operations-playbook.md`
