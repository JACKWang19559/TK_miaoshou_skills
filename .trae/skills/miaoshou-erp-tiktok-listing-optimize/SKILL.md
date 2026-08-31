---
name: miaoshou-erp-tiktok-listing-optimize
description: Diagnose and optimize TikTok Shop/TK product listings for Miaoshou ERP users, covering titles, descriptions, keywords, images, videos, category/attribute completeness, price positioning, promotions, reviews, social proof, and conversion gaps. Use for TK商品优化、Listing优化、标题描述优化、商品页转化、图片视频建议、定价促销建议、竞品商品页对比，或在妙手ERP商品编辑前生成字段级优化方案。Never save or publish products directly.
---

# Miaoshou ERP TikTok Listing Optimize

Turn product facts, Miaoshou ERP collect-box data, and user-supplied evidence into a field-level optimization proposal. Diagnose and propose only; use the existing edit, preview, and publish Skills for mutations.

## Workflow

1. Confirm target site, buyer language, product identity, current listing, price/cost context, and optimization goal.
2. Separate evidence into: Miaoshou ERP/API facts, user-provided facts, and AI inferences. Never present an inference as platform data.
3. Audit the listing with `references/listing-optimization-framework.md`.
4. If category or required attributes are uncertain, hand off to `miaoshou-erp-tiktok-category-recommend` before finalizing content.
5. If market keywords, competitor products, videos, or reviews are needed, use `miaoshouerp-tk-product-selection`; do not browse or fabricate live market evidence.
6. Produce a field-level before/after proposal with reasons, evidence, confidence, and risk. Preserve factual claims, IDs, SKU relationships, regulated attributes, and buyer language.
7. Keep price and promotion recommendations conditional on known costs and margin floors. Use `miaoshou-erp-tiktok-profit-operations` when unit economics are required.
8. For a confirmed single-product change, hand off to `miaoshou-erp-tiktok-product-edit`. For repeated scalar changes across two or more products, hand off to `miaoshou-erp-tiktok-bulk-atomic-edit`.
9. Never save, claim, publish, change price, or alter inventory in this Skill.

## Output Contract

Return:

- objective and exact product/site scope;
- evidence used and missing evidence;
- blocker, high-impact, medium-impact, and optional findings;
- field-level diff: field, current value, proposed value, reason, evidence, confidence, and risk;
- image/video shot list and content-to-listing alignment plan when relevant;
- price/promotion scenarios with explicit assumptions, not a single unsupported optimum;
- metrics to observe after implementation;
- exact handoff Skill and whether user confirmation is required.

## Hard Rules

- Optimize for the target market, not the conversation language.
- Never invent product specifications, certifications, compatibility, material, origin, efficacy, warranty, or performance claims.
- Never keyword-stuff or add irrelevant trend terms.
- Do not confuse content strategy with saved listing data. A video idea is not a product attribute.
- Treat reviews and UGC as evidence only when supplied by the user or returned by a trusted data workflow.
- Do not promise ranking, virality, conversion lift, or policy approval.
- Keep all write operations behind existing preview and confirmation gates.

## Reference

Read `references/listing-optimization-framework.md` for audit dimensions, proposal format, and handoff rules.
