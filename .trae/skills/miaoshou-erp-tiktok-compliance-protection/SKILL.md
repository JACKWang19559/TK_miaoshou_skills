---
name: miaoshou-erp-tiktok-compliance-protection
description: Diagnose TikTok Shop product/content compliance, intellectual-property, brand-abuse, customer-dispute, and evidence risks for Miaoshou ERP users. Use for TK合规检查、禁限售风险、侵权风险、商标图片视频文案风险、未授权卖家或达人滥用、假货线索、投诉取证、客服纠纷和退款沟通方案。Provides risk triage and handoffs only; never files complaints, contacts parties, edits products, or gives definitive legal advice.
---

# Miaoshou ERP TikTok Compliance Protection

Provide evidence-based risk triage. Separate product/content compliance from brand-enforcement and customer-dispute workflows.

## Workflow

1. Confirm site, product/content/account scope, incident date, requested decision, and available evidence.
2. Read `references/risk-triage.md`. For time-sensitive platform rules, route rule verification to `miaoshou-erp-tiktok-platform-rules`.
3. For a listing, retrieve complete product context through `miaoshou-erp-tiktok-product-edit` only when read access is needed; do not save.
4. Separate four tracks:
   - product/content/platform compliance;
   - intellectual-property or brand abuse;
   - customer service, refund, return, or dispute;
   - evidence and escalation readiness.
5. Classify each issue as blocker, high, medium, low, or unverified. Cite the evidence and explain what would change the classification.
6. Produce a remediation or evidence plan. Route confirmed product-field repairs to the existing TikTok edit/preview flow.
7. Keep legal conclusions, platform decisions, and enforcement outcomes explicitly uncertain unless supported by an authoritative current decision.

## Output Contract

Return scope and site; observed facts; missing evidence; risk register; affected listing/content/account element; recommended remediation; evidence checklist; escalation path; safe customer-response draft when requested; and exact handoff Skill.

## Hard Rules

- Never state that an item is prohibited, authorized, genuine, infringing, or legally compliant without adequate current evidence.
- Never invent a restricted-product list, policy clause, trademark status, authorization relationship, or enforcement result.
- Never file a complaint, send a notice, contact a seller/creator/customer, or submit an appeal.
- Never use Amazon concepts such as ASIN, FBA, or Brand Registry in a TikTok workflow.
- Preserve personal data minimally and do not expose secrets or unnecessary customer information.
- Do not modify product data or publish from this Skill.

## Reference

Read `references/risk-triage.md` for classification, evidence, and handoff rules.
