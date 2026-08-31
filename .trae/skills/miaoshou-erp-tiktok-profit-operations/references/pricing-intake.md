# Pricing Intake and Dynamic Questioning

## Entry routing

Treat any of the following as a pricing request:

- 帮我定价 / 这个产品应该卖多少钱
- 这个价格能不能卖 / 卖这个价赚多少
- 达人佣金或广告开到多少还有利润
- 按妙手模板算一下

Do not teach the user API terminology before helping them.

## Stage 1: ask only before lookup

When the request is vague, collect:

1. Target TikTok Shop site or market. This is mandatory before selecting fees/templates.
2. Seller model/site type only when the site or available templates make `cross_border` versus `mainland` material.
3. Product/SKU identity or a short product description.
4. Objective: recommend a selling price, or evaluate a known selling price.

Ask these together when natural, but lead with the missing site. Do not request a full cost table yet.

Example:

> 可以。先告诉我这款商品准备卖到哪个 TikTok Shop 站点、是什么商品，以及你是想让我推荐售价，还是评估一个已有售价。确认站点后我会先读取妙手中可用的定价模板，再只补问模板里没有的成本。

## Stage 2: select pricing source

Query templates by exact site and site type when known.

- One plausible template: show its name, currency, profit target, logistics mode, and modified time; state that it will be used unless the user objects.
- Multiple templates: show a compact numbered list using names and business differences. Ask the user to choose by number/name, not template ID.
- No template: use the exact site's current default settings and say so.
- API unavailable: ask whether the user can provide a template export; otherwise continue with explicit user inputs and label the result offline.

Do not select a template merely because it is first in the API response. Do not assume the newest template is intended.

## Stage 3: derive the question batch from the selected source

Ask only for unresolved inputs, in one batch where practical.

Always needed unless already available from Miaoshou/product evidence:

- product or landed cost, including its currency;
- units per selling item/order;
- current selling price for profit evaluation, or desired profit/margin guardrail for price recommendation.

Conditionally needed:

- actual weight for `weight` logistics;
- dimensions and unit confirmation for volume-weight/light-cargo calculation;
- actual and volume weight for `max_weight`;
- resolved official freight when the template uses `official_freight_tpl` and the endpoint supplies no amount;
- seller-paid domestic/international logistics when the template does not resolve it;
- creator commission, ad cost, return rate/loss, fulfillment, packaging, or other costs only when they are relevant to the requested scenario and absent from the selected source;
- tax-inclusive/exclusive treatment when the API field and business accounting treatment could differ.

Never ask again for a component already supplied by the selected template unless the user wants an override. Label overrides explicitly.

## Stage 4: output

For price recommendation, show at least:

- break-even price;
- target-profit candidate price;
- downside/stress price or margin result;
- any price rounding, tail, discount, or exchange-rate behavior not reproduced exactly;
- selected template/default source and missing-data confidence.

For profit evaluation, show contribution, margin, dynamic cost composition, break-even ad/commission threshold when possible, and downside sensitivity.

Phrase candidate prices as recommendations under stated assumptions. Do not claim exact parity with the Miaoshou UI unless the complete pricing formula has been verified.
