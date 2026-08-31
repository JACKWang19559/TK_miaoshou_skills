---
name: miaoshouerp-image-processing
description: Process Miaoshou ERP product images through the OpenAPI, including AI smart removal of watermarks, logos, text, or psoriasis; AI white-background matting; TikTok watermark search/application; image-text translation; result download; and supported-language lookup. Use for 妙手 ERP 图片处理、AI 智能消除、去水印/Logo/文字、白底图/抠图、图片打水印、水印列表、图片翻译、翻译语言配置. Reuse image URLs already returned by upstream collect-box product-info APIs or collect-box editing skills; also support direct URLs and local attachments that need conversion to public HTTP(S) URLs.
---

# Miaoshou ERP Image Processing

Process remote product image URLs with Miaoshou ERP OpenAPI and return source-to-result mappings.

## Workflow

1. Classify the request with the operation table below.
2. Read `references/api.md` before using exact endpoints, fields, enums, response shapes, or signing details.
3. Resolve image inputs with this priority:
   1. Reuse valid HTTP(S) image URLs already returned in the current task by a collect-box product-information API or a collect-box editing skill.
   2. Use direct image URLs supplied by the user.
   3. Only when neither source exists, use a local attachment via an available secure upload/hosting capability to obtain a temporary public URL. If none is available, state once that the Miaoshou endpoint cannot read local paths and request a direct URL; never invent or expose a local-only URL.
4. Do not ask the user to upload an image when usable upstream URLs already exist. Preserve upstream image order, deduplicate URLs, and discard blank or non-HTTP(S) values. When multiple URLs exist and the requested scope is unclear, include the ordered URL set or image count in the preview so the user can confirm the exact processing scope.
5. For translation, fetch the live supported-language configuration before submission unless a current response was already obtained in the same task.
6. Preview any processing operation before submission. Search and language lookup are read-only and may run immediately.
7. Submit a processing operation only after the user confirms the exact preview. A direct request such as “把这些图翻译成英文” authorizes preparing the preview, not consuming the API quota.
8. On confirmed processing, pass `--output-dir` when the user wants a durable local copy. Summarize original URL, status, result URL, local path, and failure reason. Keep partial successes.

## Operation Routing

| User intent | CLI command | Confirmation |
| --- | --- | --- |
| 去水印、Logo、文字、牛皮癣 | `remove` | required |
| 抠图、白底图 | `white-bg` | required |
| 查找已有水印模板 | `search-watermarks` | read-only |
| 给图片添加水印 | `watermark` | required |
| 查询可用翻译平台/语种 | `languages` | read-only |
| 翻译图片中的文字 | `translate` | required |
| 检查本地鉴权配置 | `check-config` | local read-only |

Do not route product-image-pack generation requests here. Use `miaoshouerp-product-image-generator` when the user wants newly generated marketing image sets rather than transformations of existing images.

## Safety and Data Rules

- Treat `remove`, `white-bg`, `watermark`, and `translate` as quota-consuming processing operations. Run without `--confirm` first, show the preview, then rerun the same command with `--confirm` after explicit approval.
- Never overwrite source images or claim that the original ERP product was edited. These APIs return derived image URLs.
- Never ask the user to paste AppSecret, cookies, access tokens, or authorization headers into chat. Read them from local config, environment variables, or a secure host connector.
- Never print secrets, signatures, cookies, authorization headers, or full credential-bearing requests.
- Do not send Apifox-only `X-Apifox-Debug` headers in production. Treat `timerToken` and example cookies in exported docs as debugging context, not the normal signed OpenAPI contract.
- For watermark output, require an explicit choice between preserving the source-size ratio and fixed `800x800` output.
- For smart removal, require at least one removal target and at least one area. Enforce the trace-field dependencies documented in `references/api.md`.
- Stop after one failed submission. Do not automatically retry a processing request that might consume quota.
- Treat upload as a separate preprocessing step. Do not upload local attachments to an unapproved public host or imply that Miaoshou accepts filesystem paths.
- Treat image URLs obtained from upstream collect-box reads as task-local inputs. Reuse them without asking the user to paste or upload the same images again, but do not silently expand processing to unrelated products or URLs outside the current task scope.
- Preserve exact preview parameters for confirmation. The preview includes image count and whether quota is consumed; keep user-facing confirmation to those essentials plus the operation and scene/options.

## Authentication

Use signed JSON POST requests. Configure locally with either:

- `MIAOSHOU_APP_KEY` and `MIAOSHOU_APP_SECRET`; or
- `resources/config.json`, copied locally from `resources/config.json.example`.

Optional variables are `MIAOSHOU_BASE_URL`, `MIAOSHOU_TIMEOUT`, `MIAOSHOU_ACCOUNT_ID`, `MIAOSHOU_AUTHORIZATION`, and `MIAOSHOU_COOKIE`. Do not distribute a populated `resources/config.json`.

When configuration is unknown, run the local diagnostic once:

```bash
python scripts/miaoshou_image_processing.py check-config
```

Recheck only after credentials change or authentication fails.

## Script Usage

Use `scripts/miaoshou_image_processing.py` as the only CLI entrypoint. Run `python scripts/miaoshou_image_processing.py --help` for the complete argument list.

Preview smart removal:

```bash
python scripts/miaoshou_image_processing.py remove --image-url "https://example.com/a.jpg" --source common_collect_box --common-collect-box-detail-id 123 --remove-watermark --area background
```

After confirmation, append `--confirm` to the identical command.

Preview white-background processing:

```bash
python scripts/miaoshou_image_processing.py white-bg --image-url "https://example.com/a.jpg" --image-scene 1
```

After confirmation, save the derived image locally while submitting:

```bash
python scripts/miaoshou_image_processing.py white-bg --image-url "https://example.com/a.jpg" --image-scene 1 --output-dir "C:/path/to/results" --confirm
```

Search watermark templates:

```bash
python scripts/miaoshou_image_processing.py search-watermarks --subtype normal --name "品牌" --page-no 1 --page-size 20
```

Preview watermark application while preserving the source-size ratio:

```bash
python scripts/miaoshou_image_processing.py watermark --image-url "https://example.com/a.jpg" --watermark-id "wm-123" --auto-match-image-size
```

Query language support:

```bash
python scripts/miaoshou_image_processing.py languages
```

Preview image translation while preserving brand text:

```bash
python scripts/miaoshou_image_processing.py translate --image-url "https://example.com/a.jpg" --source-lang zh --target-lang en --platform aeAi --exclude-brand
```

## Result Handling

- Root success is `result=success`; root failure may expose `code` and `reason`.
- Do not infer batch success from HTTP 200 alone. Inspect every per-image `result` field.
- Smart removal returns usage counters. Report them without promising remaining quota.
- Translation separates normal results from grouped error results. Flatten failures into per-URL rows when presenting them.
- If a response omits a result URL, report it as unavailable rather than guessing.
- When `--output-dir` is present, read `localArtifacts[]`. A failed download does not change a successful API processing result; report the remote URL and local download failure separately.

## Failure Handling

- `signMissing`: signed headers are absent.
- `signExpired`: check clock drift and seconds-level timestamp.
- `signInvalid`: verify the exact compact JSON body, path, AppKey, and AppSecret.
- `appNotFound`: app key is wrong, disabled, or not approved.
- `appNoPermission`: the app lacks permission for the endpoint.
- `ipNotInWhitelist`: add the caller IP to the Miaoshou account whitelist.
- Unsupported language pair: show available platform/source/target combinations from the live config and do not submit translation.
- Partial batch failure: keep successful result URLs and report failed URLs with API reasons.
