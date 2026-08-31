# Miaoshou ERP Image Processing API

Use this reference for exact endpoints, request contracts, response fields, validation, and production authentication.

## Contents

- [Transport and authentication](#transport-and-authentication)
- [AI smart removal](#ai-smart-removal)
- [AI white background](#ai-white-background)
- [Search watermark templates](#search-watermark-templates)
- [Apply watermark](#apply-watermark)
- [Get translation language configuration](#get-translation-language-configuration)
- [Translate image text](#translate-image-text)
- [Result and error handling](#result-and-error-handling)

## Transport and Authentication

Production requests use:

- Base URL: `https://openapi-erp.91miaoshou.com` unless configured otherwise.
- Method: `POST`.
- Content type: `application/json`.
- Headers: `x-app-key`, `x-timestamp`, and `x-sign`.
- Timestamp: Unix seconds. Requests normally expire after 300 seconds of clock drift.

Sign the exact JSON body sent over the wire:

```text
signContent = appSecret + path + timestamp + appKey + bodyJson + appSecret
x-sign = lowercase_hex(HmacSHA256(key=appSecret, message=signContent))
```

Use only the path in `path`, with no domain or query string. Use compact UTF-8 JSON. When an endpoint has no body, use an empty string for `bodyJson` and send an empty POST body.

The exported Apifox specifications contain `timerToken`, `Cookie`, and `X-Apifox-Debug` examples. Do not treat those as the normal production contract. Optional account-context headers may be injected from secure local configuration only when the deployment requires them.

## AI Smart Removal

`POST /open/v1/product/common/image_removal/remove_image`

### Request

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `imageUrls` | yes | string[] | Remote image URLs |
| `traceInfo` | yes | object | Business-source trace |
| `removeConfig` | yes | object | Removal targets and regions |

`traceInfo`:

| Field | Required | Notes |
| --- | --- | --- |
| `imageRemovalSource` | yes | `collect_box`, `collect_box_add`, `common_collect_box`, `common_collect_box_add`, `item`, or `item_add` |
| `collectBoxDetailId` | conditional | Required when source is `collect_box` |
| `commonCollectBoxDetailId` | conditional | Required when source is `common_collect_box` |
| `platform` | conditional | Required for platform collect-box and online-product sources; the bundled CLI enforces it for `collect_box*` and `item*` |

`removeConfig`:

| Field | Required | Values |
| --- | --- | --- |
| `isRemoveWatermark` | yes | `0` or `1` |
| `isRemoveLogo` | yes | `0` or `1` |
| `isRemoveText` | yes | `0` or `1` |
| `isRemovePsoriasis` | no | `0` or `1` |
| `removeAreas` | yes | One or both of `background`, `subject` |

Example:

```json
{"imageUrls":["https://example.com/a.jpg"],"traceInfo":{"imageRemovalSource":"common_collect_box","commonCollectBoxDetailId":123},"removeConfig":{"isRemoveWatermark":1,"isRemoveLogo":0,"isRemoveText":0,"isRemovePsoriasis":0,"removeAreas":["background"]}}
```

### Response

Read `data.imageRemovalUrlResultList[]`:

- `result`: `success` or `fail`.
- `reason`: single-image failure reason.
- `oriImageUrl`: source URL.
- `newImageUrl`: derived URL.

Usage metadata may include `imageRemovalUseNum`, `appResourceCode`, `appResourceUseNum`, and `freeUseNum`.

## AI White Background

`POST /open/v1/product/picture/matting/auto_ai_matting_multi`

### Request

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `imgUrls` | yes | string[] | URLs; duplicates should be removed |
| `imageScene` | yes | integer | `1` product, `2` description, `3` SKU/product attribute, `4` certificate, `5` size chart |

Example:

```json
{"imgUrls":["https://example.com/a.jpg"],"imageScene":1}
```

### Response

Read `data.imgMattingList[]`: `result`, `width`, `height`, `md5`, `newImageUrl`, and `oriImageUrl`.

## Search Watermark Templates

`POST /open/v1/product/item/tiktok/watermark/search_watermark_list`

This operation is read-only.

### Request

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `watermarkIds` | no | string | Multiple IDs separated by commas |
| `watermarkName` | no | string | Fuzzy name search |
| `watermarkSubType` | yes | string | `normal` or `byLayer` |
| `pageNo` | yes | integer | Minimum 1 |
| `pageSize` | yes | integer | Minimum 1 |

### Response

Read `data.watermarkList[]` and `data.total`. Each item may contain `watermarkId`, `appAccountId`, `platform`, `watermarkImageUrl`, `watermarkType`, `watermarkSubType`, and `name`.

## Apply Watermark

`POST /open/v1/product/item/tiktok/watermark/watermark_images`

### Request

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `imageUrls` | yes | string[] | Source URLs |
| `watermarkId` | yes | string | Select with the search endpoint |
| `collectBoxDetailId` | no | integer | Send when available |
| `isAutoMatchImageSize` | yes | boolean | `true` preserves proportional sizing; `false` outputs `800x800` by default |

### Response

Read `data.watermarkDetail[]`: source `imageUrl`, `result`, derived `watermarkImageUrl`, and failure `msg`.

## Get Translation Language Configuration

`POST /open/v1/product/common/translate/get_support_language_config`

This operation is read-only and has no request body.

Read `data.supportLanguageConfig`. The documented shape is:

```text
{platform: {mode: {sourceLanguage: [targetLanguages]}}}
```

Modes include `realTime` and `idle`. Documentation lists `aeAi`, `tosoiot`, and `ykt`; the translation endpoint also documents `ali`. Always trust the live configuration over a hard-coded platform list.

## Translate Image Text

`POST /open/v1/product/common/translate/translate_image`

### Request

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `imageUrls` | yes | string[] | Source URLs |
| `sourceLang` | yes | string | Validate against live configuration |
| `targetLang` | yes | string | Validate against live configuration |
| `translatePlatform` | yes | string | Validate against live configuration |
| `noTranslateImageTextOptions` | no | string[] | `textInTheProduct` and/or `brand` |

Example:

```json
{"imageUrls":["https://example.com/a.jpg"],"sourceLang":"zh","targetLang":"en","translatePlatform":"aeAi","noTranslateImageTextOptions":["brand"]}
```

### Response

Read:

- `data.translateImageUrlResultList[]`: `oriImageUrl`, `newImageUrl`, and `result`.
- `data.translateImageUrlErrorResultList[]`: `failImageCount`, `failImageUrls`, and `reason`.

## Result and Error Handling

All endpoints wrap data with root `result` and `code`; root failures may include `reason`. HTTP 200 does not guarantee every image succeeded.

Common authorization codes:

| Code | Likely cause |
| --- | --- |
| `signMissing` | Missing signed headers |
| `signExpired` | Clock drift or wrong timestamp unit |
| `signInvalid` | Path/body/AppKey/AppSecret mismatch |
| `appNotFound` | App missing, disabled, or not approved |
| `appNoPermission` | Endpoint permission missing |
| `ipNotInWhitelist` | Caller IP is not allowed |

For processing calls, do not automatically retry after a timeout or ambiguous network failure because the original request may have reached the service and consumed quota.

