---
name: miaoshouerp-ai-product-polish
description: Use Miaoshou ERP AI public services to generate or polish ecommerce product titles, descriptions, and SKU sales specification names. Use when a user wants AI-assisted title/description rewriting or translation, keyword inclusion, negative-word exclusion, image-assisted product copy, supported AI/language discovery, or TikTok SKU specification normalization through Miaoshou ERP.
---

# Miaoshou ERP AI Product Polish

Generate polished product copy and SKU sales specifications through the Miaoshou ERP AI public-service APIs. Preview requests by default; make live calls only when the user asks and local session credentials are available.

## Responsibilities

- Discover the currently supported AI names and target-language codes.
- Generate a title, a description, or both from product context.
- Preserve user-supplied facts, keywords, exclusions, platform, site, category, and image context.
- Polish TikTok SKU property names and values without losing IDs or image associations.
- Return every generated candidate and identify partial failures per result type.

## Non-Responsibilities

- Do not save generated text back to a collect box or online product.
- Do not publish products.
- Do not invent product facts, brands, certifications, materials, dimensions, compatibility, safety claims, or category IDs.
- Do not use this Skill as a substitute for platform-specific compliance or listing validation.

## Standard Workflow

1. Determine the requested output: `title`, `notes` (description), `sku-spec`, or a combination.
2. Read `references/api.md` before selecting exact fields, enums, or response paths.
3. Preserve the original content and gather only missing required context: platform, function module, AI name, and language code. For SKU specification polishing, require the complete `skuPropertyList`.
4. Query `ai-names` or `languages` when the requested value is absent or uncertain. Do not guess a language code or unsupported model.
5. Build a preview with `scripts/miaoshou_ai_polish.py`. Show method, path, and payload; the preview never exposes credentials.
6. Check the preview for unsupported fields and semantic risks. If generated claims depend on facts not supplied by the user, flag them instead of treating them as verified.
7. Add `--execute` only when the user requested a live generation and credentials are locally configured.
8. Return original versus generated candidates, requested language, AI name, and any API `code`, `reason`, or per-type failure.

## Safety and Data Rules

- Load session data only from `resources/config.json`, an explicitly selected config file, or environment variables. Never ask the user to paste cookies or tokens into chat.
- Never print `Cookie`, `timerToken`, authorization values, or complete request headers.
- Do not send `X-Apifox-Debug` unless the user explicitly requests debugging in an authorized test environment.
- Treat generated content as a proposal. This API does not save or publish, but downstream writes still require the relevant edit workflow and confirmation rules.
- For edit modules, require the correct product identifier: `functionModuleProductId` for title/description and `productId` for SKU specifications.
- For SKU specifications, preserve `attrId`, `attrValueId`, `imgUrl`, and `supplementarySkuImageUrls`; change only the returned names/values unless the user explicitly requests otherwise.
- The SKU specification endpoint currently supports only `platform=tiktok` and `aiName=douBao1.6` according to the supplied API document.

## Script Usage

The only CLI entry is `scripts/miaoshou_ai_polish.py`. Commands preview by default and send a request only with `--execute`.

```bash
python scripts/miaoshou_ai_polish.py ai-names
python scripts/miaoshou_ai_polish.py languages
python scripts/miaoshou_ai_polish.py product-info --input request.json
python scripts/miaoshou_ai_polish.py sku-spec --input sku_request.json
```

Use `--payload '{...}'` for compact inline JSON or `--input path.json` for a file. Put shared options after the command:

```bash
python scripts/miaoshou_ai_polish.py product-info --input request.json --execute
```

Run `python scripts/miaoshou_ai_polish.py --help` and the subcommand help for exact options. Copy `resources/config.json.example` to `resources/config.json` only on the local machine; never distribute the populated file.

## References

- Read `references/api.md` for exact endpoints, required fields, enums, response shapes, and request examples.

