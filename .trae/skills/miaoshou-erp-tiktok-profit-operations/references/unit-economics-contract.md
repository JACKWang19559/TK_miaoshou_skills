# Unit Economics Contract

All monetary values must use one currency and one item/order grain.

## Unit input

Required: `selling_price`, `product_cost` and one explicit currency/item-or-order grain.

Preferred dynamic input: `pricing_context`, generated from the current Miaoshou saved template or site defaults. It contains `rate_components`, `amount_components`, provenance, ignored fields, and missing inputs. The calculator merges explicit scenario overrides without changing the source snapshot.

Optional user/product-specific fixed costs: `inbound_shipping`, `fulfillment_cost`, `outbound_shipping`, `packaging_cost`, `other_fixed_cost`, `return_processing_cost`, `return_shipping_cost`.

Optional scenario rates from 0 to 1: `creator_commission_rate`, `ad_cost_rate`, `return_rate`, `unrecoverable_return_fraction`, `target_contribution_margin`. Legacy explicit platform/payment rates remain accepted only as visible user overrides or offline fallback.

Base variable cost is product-specific fixed costs plus dynamically resolved amount components and selling price multiplied by dynamically resolved rate components. Buyer-paid logistics is a revenue offset and is not a seller cost.

Expected return loss is `return_rate * (return_processing + return_shipping + product_cost * unrecoverable_fraction)`.

Contribution is selling price minus base variable cost and expected return loss. The model does not separately reverse revenue for returns. If the user's accounting treatment differs, adjust the model before calculating.

## Price recommendation input

Required: `product_cost`, `pricing_context`, and exactly one of `target_contribution_margin` (0-1) or `target_profit_amount`. Add the same product-specific fixed costs and return inputs used by the unit model.

- target-margin candidate = fixed and amount costs / (1 - total price-based rate - target margin)
- target-amount candidate = (fixed and amount costs + target profit amount) / (1 - total price-based rate)

The output is a mathematical pre-rounding candidate. Do not automatically reproduce template `discount`, `priceTail`, `priceProcessDecimalType`, or exchange-rate behavior without a verified ordering contract.

## Inventory input

Required: `on_hand`, `daily_demand`, `lead_time_days`, `review_period_days`, `safety_days`.

Optional: `on_order`, `reserved`, `minimum_order_quantity`, `unit_landed_cost`.

- available stock = on hand + on order - reserved;
- stock cover = available stock / daily demand;
- reorder point = daily demand * (lead time + safety days);
- target stock = daily demand * (lead time + review period + safety days);
- suggested order = max(0, target stock - available stock), rounded up to MOQ when provided.
