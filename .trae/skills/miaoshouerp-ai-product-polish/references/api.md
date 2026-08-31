# Miaoshou ERP AI Polish API Reference

Use this reference for exact request fields and response paths. All four endpoints are `POST`, accept JSON request bodies, and are under `/open/v1/product/common/open_ai/`.

## Contents

- [Runtime and session context](#runtime-and-session-context)
- [Get supported AI names](#get-supported-ai-names)
- [Get supported languages](#get-supported-languages)
- [Generate title and description](#generate-title-and-description)
- [Polish SKU sales specifications](#polish-sku-sales-specifications)
- [Errors and response handling](#errors-and-response-handling)

## Runtime and session context

- Default base URL used by the helper: `https://openapi-erp.91miaoshou.com`; override it when the deployed environment uses another host.
- Optional query parameter: `timerToken`.
- Session header documented by the supplied specification: `Cookie`.
- `X-Apifox-Debug: 1` is a test/debug header. The helper omits it unless `--apifox-debug` is explicitly set.
- Keep cookies and tokens in local configuration or environment variables, not command output or chat.

Environment variables:

| Variable | Purpose |
| --- | --- |
| `MIAOSHOU_AI_BASE_URL` | Override API base URL |
| `MIAOSHOU_COOKIE` | Session cookie |
| `MIAOSHOU_TIMER_TOKEN` | Optional `timerToken` query value |
| `MIAOSHOU_AI_TIMEOUT` | Request timeout in seconds |

## Get supported AI names

`POST /open/v1/product/common/open_ai/get_generate_product_info_support_ai_name_list`

No JSON fields are required. The documented response path is `data.aiNameList`.

Documented candidates are `deepSeekR1`, `douBao1.6`, and `tongYiQianWen`; query the endpoint instead of assuming this list is current.

## Get supported languages

`POST /open/v1/product/common/open_ai/get_language_name_code_map`

No JSON fields are required. The response path is `data.languageNameCodeMap`, where keys are display names and values are codes such as `zh-TW` or `th`.

For `generate_product_info`, `languageName` expects the returned code even though the field name says “name”.

## Generate title and description

`POST /open/v1/product/common/open_ai/generate_product_info`

Required request fields:

| Field | Type | Notes |
| --- | --- | --- |
| `generateTypeList` | string[] | Values: `title`, `notes` |
| `functionModule` | string | `createCollectBox`, `editCollectBox`, `createItem`, or `editItem` |
| `platform` | string | Target platform |
| `aiName` | string | Use a value returned by the AI-name endpoint |
| `title` | string | Original title/context; required even for description generation |
| `languageName` | string | Use a code returned by the language endpoint |

Conditional field:

- `functionModuleProductId` is required when `functionModule` is `editCollectBox` or `editItem`.

Optional fields:

| Field | Type | Notes |
| --- | --- | --- |
| `originalContent` | string | Original description used for `notes` generation |
| `titleLengthLimit` | integer | Desired title length limit |
| `keywordsList` | string[] | Keywords to incorporate where truthful |
| `negativeWordsList` | string[] | Terms to exclude |
| `categoryName` | string | Human-readable category |
| `site` | string | Target site |
| `cid` | string | Category ID; do not invent it |
| `imageInfoList` | object[] | Image context items |

Each `imageInfoList` item requires `imageUrl`; optional `imageSource` is `productImage` or `otherImage`.

Example:

```json
{
  "generateTypeList": ["title", "notes"],
  "functionModule": "createCollectBox",
  "platform": "tiktok",
  "aiName": "douBao1.6",
  "title": "Portable rechargeable desk fan",
  "originalContent": "Three speeds, USB-C charging, compact base.",
  "titleLengthLimit": 120,
  "languageName": "en",
  "keywordsList": ["portable", "rechargeable"],
  "negativeWordsList": ["medical grade"],
  "categoryName": "Desk Fans"
}
```

Response candidates:

- `data.titleResult.result` and `data.titleResult.contents`
- `data.notesResult.result` and `data.notesResult.contents`

Inspect each requested result independently because one type can fail while the other succeeds.

## Polish SKU sales specifications

`POST /open/v1/product/common/open_ai/generate_sku_spec_name`

Required request fields:

| Field | Type | Notes |
| --- | --- | --- |
| `platform` | string | Currently only `tiktok` |
| `aiName` | string | Currently only `douBao1.6` |
| `functionModule` | string | `createCollectBox`, `editCollectBox`, `createItem`, or `editItem` |
| `skuPropertyList` | object[] | Complete SKU property list |

Optional fields:

- `title`: original title used as AI context.
- `languageName`: target language name/code as accepted by the API; the document says the default is “current language”.
- `productId`: required in practice for edit modules according to the field description.

`skuPropertyList` item:

| Field | Type | Notes |
| --- | --- | --- |
| `attrName` | string | Property name such as `Color` |
| `attrId` | string | May be empty |
| `attrValueList` | object[] | Property values |

Each property value carries `attrValueId`, `attrValue`, `imgUrl`, and `supplementarySkuImageUrls`. Preserve all IDs and image references when applying the returned names.

Example:

```json
{
  "platform": "tiktok",
  "title": "Women's ribbed crew socks",
  "aiName": "douBao1.6",
  "languageName": "English",
  "functionModule": "createCollectBox",
  "skuPropertyList": [
    {
      "attrName": "颜色",
      "attrId": "",
      "attrValueList": [
        {
          "attrValueId": "",
          "attrValue": "米白",
          "imgUrl": "",
          "supplementarySkuImageUrls": []
        }
      ]
    }
  ]
}
```

Response paths:

- `data.newSkuPropertyList`
- `data.reasoningContent` (model-dependent; do not expose hidden reasoning as authoritative product facts)
- `data.openaiRequestLogId`

The source document's prose example for `newSkuPropertyList` uses a simplified `name/valueList` shape while its schema repeats the original `attrName/attrValueList` shape. Treat the live response as authoritative and validate either shape before downstream use.

## Errors and response handling

Success responses contain top-level `result`, `code`, and `data`. Error responses may contain `result`, `code`, and `reason`.

- Report `code` and `reason` without credentials or complete request headers.
- Treat a non-success top-level `result`, HTTP error, missing requested result block, or per-type `result=fail` as a failure.
- Preserve the original input so users can compare or retry safely.

