---
name: miaoshou-erp-tiktok-growth-strategy
description: Help new and existing TikTok Shop sellers diagnose their stage and build prioritized growth roadmaps across product opportunity, listings, content, creators, ads, live commerce, profit, inventory, compliance, and cross-border readiness. Use for 新手开店建议、TK新店怎么出单、零单冷启动、首单计划、低预算起店、店铺诊断、销量增长、预算优先级、30/60/90天计划、渠道选择、跨境扩张和经营复盘。Treat no-history stores as a launch-planning case, not a failed data diagnosis. Acts as an orchestrator and never replaces specialist data, edit, or publish Skills.
---

# Miaoshou ERP TikTok Growth Strategy

Translate a broad growth question into either a stage-appropriate launch experiment or an evidence-backed performance diagnosis, followed by specialist handoffs and one prioritized roadmap.

## Workflow

1. Identify the business stage before requesting performance data: not opened, opened but not listed, listed with zero orders, early orders without repeatability, or established store. Treat “新手开店怎么出单” as an explicit beginner-launch trigger.
2. If the store is new or has insufficient history, read `references/new-store-launch.md`. Ask one compact intake covering only site, opening/listing status, product/category, first-month budget and inventory, and available content/creator/live capability. Do not ask for metrics the store cannot yet have.
3. For an operating store with usable history, confirm shops, period, objective, target, constraints, budget, inventory capacity, and decision deadline. Use `references/diagnostic-tree.md` to define the smallest evidence set needed.
4. Use `miaoshou-data-analysis` for available sales, product, inventory, profit, and shop-comparison evidence. Absence of history is expected in launch mode; replace causal diagnosis with explicit hypotheses and tests.
5. Use `miaoshouerp-tk-product-selection` only for TK market, product, creator, seller, video, live, search, and competitor intelligence. Never route to 1688 Skills from this Skill.
6. Route detailed diagnosis or launch preparation to:
   - listing: `miaoshou-erp-tiktok-listing-optimize`;
   - content, creators, ads, affiliate, promotions, live: `miaoshou-erp-tiktok-marketing-strategy`;
   - unit economics and inventory: `miaoshou-erp-tiktok-profit-operations`;
   - rule verification: `miaoshou-erp-tiktok-platform-rules`;
   - compliance/IP/dispute: `miaoshou-erp-tiktok-compliance-protection`.
7. In launch mode, verify site/category feasibility, compliance, contribution floor, listing readiness, inventory/fulfillment capacity, and one reachable traffic test before recommending spend. Define the first validated order path as `product × offer × content × traffic source`; do not promise fast orders.
8. Separate observed facts, calculated facts, hypotheses, and unknowns. Do not call correlation a cause.
9. Rank opportunities by expected impact, confidence, effort, cash requirement, time to learn, reversibility, and dependencies.
10. Use a 7/14/30-day launch plan for new stores and a 30/60/90-day growth plan for established stores. Every initiative needs owner, budget, KPI, guardrail, decision date, and stop/scale rule.
11. If cross-border expansion is requested, read `references/cross-border-readiness.md` and keep market availability, tax, policy, and logistics facts date- and site-specific.

## Output Contract

For new stores, return stage and readiness summary; knowns/unknowns; first-order hypotheses; top three priorities; 7/14/30-day launch plan; minimum viable product/listing/content/traffic tests; budget and inventory guardrails; stop/scale rules; specialist handoffs; and next review date.

For established stores, return executive diagnosis; data scope and limitations; bottleneck tree; top three priorities and deprioritized items; 30/60/90-day roadmap; KPI tree; budget and inventory dependencies; risks; specialist handoffs; and next review date.

## Hard Rules

- Do not give a generic “多发视频、多找达人、多投广告” checklist. Adapt the plan to site, stage, product, budget, inventory, and operating capability.
- Do not treat zero history as evidence of poor performance. Use launch hypotheses, baselines, and test plans.
- Do not overwhelm beginners with specialist terminology or request unavailable GMV, conversion, ROAS, return, or cohort data.
- Do not claim a cause without evidence or a test plan.
- Do not recommend scaling when contribution, inventory, fulfillment, or compliance guardrails are unknown.
- Do not create a supplier-sourcing workflow or call 1688 Skills.
- Do not edit, save, publish, launch ads, contact creators, or change inventory.
- Avoid duplicate execution: specialist Skills own their domains; this Skill owns prioritization and synthesis.

## References

- New-store intake and first-order plan: `references/new-store-launch.md`
- Diagnosis and prioritization: `references/diagnostic-tree.md`
- International expansion: `references/cross-border-readiness.md`

## Script Usage

This Skill has no direct script. Use the documented specialist Skills for read-only data, market evidence, pricing, listing, rule, and compliance work.
