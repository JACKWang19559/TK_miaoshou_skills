# TK_miaoshou_skills

> 妙手 ERP（Miaoshou ERP）× TikTok Shop 跨境铺货自动化 **Trae 技能集（Skills）**。
> 覆盖从 **1688 选品采集 → 公共采集箱 → 认领到 TikTok → 站点定价 → 类目/属性匹配 →
> 商品编辑补齐（尺码表/材质/价格/库存/物流）→ 发布就绪诊断 → 上架发布 → Listing
> 优化 / 合规 / 增长** 的完整链路。

本仓库以 [Trae](https://www.trae.ai/) / Claude Code 风格的 **Skill** 形式组织：每个技能是一个
含 `SKILL.md`（触发条件 + 工作流 + 安全规则）、`scripts/`（可直接运行的 Python 脚本）、
`references/`（API 与方法论文档）的目录。脚本直连**妙手开放平台 OpenAPI**（HmacSHA256 签名）。

---

## 一、能力全景（16 个技能）

### 上游：选品 / 采集 / 认领

| 技能 | 类型 | 作用 |
| --- | --- | --- |
| `mss-1688-sourcing` | 方法论 | 妙手 API 从 1688 选品采集到公共采集箱的工作流（选品定位、链接获取、批量采集、核验） |
| `miaoshou-erp-source-import` | API 脚本 | 把 1688 / 速卖通等货源链接批量采集进妙手**公共采集箱** |
| `miaoshou-erp-common-collectbox-manage` | API 脚本 | 公共采集箱商品查询/新增/编辑/删除、批量改价改库存改 SKU |
| `miaoshou-erp-product-claim` | API 脚本 | 把公共采集箱商品**认领**到 TikTok / Ozon / Temu / Shopee 等平台采集箱 |
| `miaoshou-erp-shop-query` | API 脚本 | 查询授权店铺列表、shopId、站点、跨境/本土状态 |

### 中游：定价 / 类目 / 编辑 / 发布

| 技能 | 类型 | 作用 |
| --- | --- | --- |
| `mss-vn-pricing` | 计算工具 | 越南站人民币成本 → 越南盾三档心理定价（保本/引流/常规/利润），含费率模板 |
| `miaoshou-erp-tiktok-profit-operations` | API+方法论 | 定价、单位经济模型、佣金/费率/物流/库存周转/经营风险分析 |
| `miaoshou-erp-tiktok-category-recommend` | API 脚本 | 叶子类目推荐、类目属性元数据、必填项识别 |
| `miaoshou-erp-tiktok-product-edit` | API 脚本 | TikTok 采集箱商品**详情 / 保存 / 诊断**（`detail` / `save` / `diagnose`） |
| `miaoshou-erp-tiktok-apparel-readiness` | 脚本+方法论 | **服装类目发布就绪闭环**：生成本地化尺码表图 → 公网托管 → 补必填属性（材质）→ 整包改价/库存/尺寸 → 保存验证 |
| `miaoshou-erp-tiktok-product-publish` | API 脚本 | 发布前检查、认领确认、提交发布任务、队列状态查询 |

### 下游：优化 / 合规 / 增长 / AI

| 技能 | 类型 | 作用 |
| --- | --- | --- |
| `miaoshou-erp-tiktok-listing-optimize` | 方法论 | 标题/描述/关键词/图片/视频/定价/促销/评论的转化诊断与字段级优化方案 |
| `miaoshou-erp-tiktok-compliance-protection` | 方法论 | 禁限售、知识产权、商标滥用、假货、客服纠纷等合规风险分级与交接 |
| `miaoshou-erp-tiktok-growth-strategy` | 方法论 | 新手冷启动、店铺阶段诊断、30/60/90 天增长路线、渠道选择 |
| `miaoshouerp-ai-product-polish` | API 脚本 | 调用妙手 AI 生成/润色标题、描述、SKU 规格名，多语言翻译 |
| `miaoshouerp-image-processing` | API 脚本 | AI 去水印/Logo/文字、白底抠图、打 TikTok 水印、图片翻译 |

> 不含货叮咚（HDD）浏览器铺货技能——那是另一套 ERP 的浏览器自动化路线，非妙手 OpenAPI 体系。

---

## 二、目录结构

```
TK_miaoshou_skills/
├── README.md
├── LICENSE                      # MIT
├── requirements.txt
├── .gitignore
└── .trae/
    └── skills/                  # 直接对应 Trae 项目的 .trae/skills 目录
        ├── miaoshou-erp-shop-query/
        │   ├── SKILL.md
        │   ├── scripts/shop_list.py
        │   ├── references/api_reference.md
        │   └── resources/config.json.example   # 凭证模板（真实 config.json 不入库）
        ├── miaoshou-erp-tiktok-product-edit/
        ├── miaoshou-erp-tiktok-apparel-readiness/
        │   └── scripts/  gen_sizechart.py / upload_image.py / build_edit_payload.py
        └── ...（共 16 个技能）
```

---

## 三、环境前提与配置（重要）

### 3.1 账号与开放平台应用

1. 拥有**妙手 ERP** 账号，并已授权 TikTok 店铺（妙手内完成店铺授权）。
2. 登录妙手 → 「开放平台」→ **创建应用** → 提交审核 → **审核通过后**使用。
3. 拿到应用凭证 `AppKey` 与 `AppSecret`。
4. 若账号开启了 **IP 白名单**，需把运行脚本的机器 IP 加入白名单（同账号下所有应用共享）。

### 3.2 Python 环境

- Python **3.10+**（开发实测 3.11）；Windows / macOS / Linux 均可。
- 安装依赖：

```bash
pip install -r requirements.txt
```

第三方依赖仅两个：`requests`（API 请求）、`Pillow`（尺码表图生成）；其余均为标准库。

### 3.3 配置凭证（二选一）

**方式 A：配置文件**。对每个带 `resources/` 的技能，把模板复制成真实配置并填入：

```bash
cp .trae/skills/miaoshou-erp-tiktok-product-edit/resources/config.json.example \
   .trae/skills/miaoshou-erp-tiktok-product-edit/resources/config.json
```

```json
{
  "app_key": "你的 AppKey",
  "app_secret": "你的 AppSecret",
  "base_url": "https://openapi-erp.91miaoshou.com",
  "timeout": 30
}
```

**方式 B：环境变量**（推荐，CI/多技能共享）：

```bash
# Windows PowerShell
$env:MIAOSHOU_APP_KEY="你的AppKey"
$env:MIAOSHOU_APP_SECRET="你的AppSecret"
# 可选：$env:MIAOSHOU_BASE_URL="https://openapi-erp.91miaoshou.com"
```

```bash
# macOS / Linux
export MIAOSHOU_APP_KEY="你的AppKey"
export MIAOSHOU_APP_SECRET="你的AppSecret"
```

> 脚本读取顺序：环境变量优先，其次 `resources/config.json`。
> **`resources/config.json` 已被 `.gitignore` 忽略，切勿提交。**

### 3.4 签名鉴权机制

所有妙手 OpenAPI 均为 `POST` + `Content-Type: application/json`，带三个签名头：
`x-app-key`、`x-timestamp`（秒级 Unix 时间戳，±300 秒有效）、`x-sign`。

```text
sign = HmacSHA256(appSecret, appSecret + path + timestamp + appKey + bodyJson + appSecret)
```

- `path` 只含 API 路径（如 `/open/v1/order/create`），不含域名和 query；
- `bodyJson` 必须与请求体**完全一致**的 JSON 字符串（无请求体时用空字符串）；
- `x-sign` 为小写十六进制 HmacSHA256。

常见鉴权错误码：`signMissing`（缺头）、`signExpired`（时钟/时间戳）、
`signInvalid`（签名/body/path/secret 不匹配）、`appNotFound`（AppKey 错/未审核/停用）、
`appNoPermission`（应用无该接口权限）、`ipNotInWhitelist`（IP 不在白名单）。

---

## 四、安装到你的 Trae 项目

把本仓库的 `.trae/skills/` 下的技能目录复制到你 Trae 项目的 `.trae/skills/` 即可：

```bash
# 例：复制全部技能到目标项目
cp -r .trae/skills/* /你的项目/.trae/skills/
```

随后按 3.3 配置凭证。Trae 会根据每个 `SKILL.md` 的 `description` 自动判断何时调用。

---

## 五、全流程 Quickstart（越南站服装为例）

```text
1688 选品 → 采集 → 认领 → 定价 → 类目/属性 → 编辑补齐 → 诊断 → 发布
```

```bash
# 0) 查授权店铺，拿 shopId / 站点
py .trae/skills/miaoshou-erp-shop-query/scripts/shop_list.py ...

# 1) 采集 1688 链接到公共采集箱（详见 source-import 的 SKILL.md）
# 2) 公共采集箱认领到 TikTok 店铺采集箱
py .trae/skills/miaoshou-erp-product-claim/scripts/claim_to_platform.py ...

# 3) 越南站定价（人民币成本 → 越南盾三档价）
py .trae/skills/mss-vn-pricing/scripts/vn_pricing.py ...

# 4) 拉 TikTok 采集箱商品详情，拿 detailId 与 ossMd5（乐观锁）
py .trae/skills/miaoshou-erp-tiktok-product-edit/scripts/tiktok_collectbox.py \
    detail <detailId> --mode shop --shop-id <shopId> --site VN

# 5) 服装类目：生成越南语尺码表图 → 上传公网图床拿直链
py .trae/skills/miaoshou-erp-tiktok-apparel-readiness/scripts/gen_sizechart.py \
    --site VN --out sizechart.png
py .trae/skills/miaoshou-erp-tiktok-apparel-readiness/scripts/upload_image.py sizechart.png

# 6) 深拷贝详情整包改价/库存/重量/尺寸/尺码表/属性，生成 edit.json
py .trae/skills/miaoshou-erp-tiktok-apparel-readiness/scripts/build_edit_payload.py \
    --detail detail.json --out edit.json \
    --price 299000 --stock 555 --weight 0.4 \
    --length 30 --width 25 --height 3 \
    --size-chart-url "<第5步直链>" --attributes-file attrs.json

# 7) 保存（回传 ossMd5）
py .trae/skills/miaoshou-erp-tiktok-product-edit/scripts/tiktok_collectbox.py \
    save <detailId> --mode shop --shop-id <shopId> --site VN \
    --oss-md5 "<ossMd5>" --file edit.json

# 8) 诊断达「可发布」
py .trae/skills/miaoshou-erp-tiktok-product-edit/scripts/tiktok_collectbox.py \
    diagnose <detailId> --mode shop --shop-id <shopId> --site VN

# 9) 发布到 TikTok 店铺
py .trae/skills/miaoshou-erp-tiktok-product-publish/scripts/tiktok_publish.py \
    publish --detail-ids <detailId> --shop-ids <shopId>
```

> 各脚本完整参数以对应技能目录下的 `SKILL.md` 与 `python <script> --help` 为准。
> 写操作（认领、保存、发布）均应在明确确认后执行。

---

## 六、实测避坑指南

1. **价格双字段（越南站）**：SKU 同时有 `price` 与 `priceIncludeVat`。越南站**前台零售价取
   含税价 `priceIncludeVat`**；该值在采集/认领时由系统按货源价自动算成高溢价建议价。
   **只改 `price` 不改 `priceIncludeVat`，上架后前台仍显示系统高价。** 改价务必两个字段都写成
   目标售价（`build_edit_payload.py` 已自动同步）。发布后务必到 TikTok 卖家中心核对前台价。
2. **发布后无法用妙手 API 改在线价**：妙手开放平台只有「发布前（采集箱）」端点，没有在线商品
   改价接口。商品一旦发布，在线 listing 价格只能在 TikTok 卖家中心改。
3. **服装尺码表必须是公网图片 URL**：平台只接受 JPG/PNG/WEBP 公网地址，妙手保存时拉取转存 CDN；
   临时图床（如 litterbox 72h）需在有效期内发布。
4. **乐观锁 ossMd5**：每次详情返回的 `ossMd5` 是版本号，`save` 必须回传；保存成功返回新 ossMd5，
   下次编辑用新值。
5. **整包回写**：保存接口需回传完整 `shopCollectItemInfo` 对象（用 `build_edit_payload.py` 深拷贝
   生成），只传改动片段会抹掉标题/描述/图片/规格。
6. **SKU 遍历**：跳过 `isDelete=1` 的 SKU；改库存时同步 `shopIdToWarehouseIdAndStockMap` 多仓库存。
7. **必填属性按站点/类目不同**：如越南服装类目 cid 601284 必填「材质」；制造商/责任人/EPR 仅
   欧盟站点强制。用 category-recommend 拉类目元数据筛 `必填` 项，值要与 1688 货源标注一致。
8. **尺码表数据为通用参考值**，非货源实测；有工厂真实尺寸请用 `gen_sizechart.py --data` 覆盖；
   越南语等带变音符号的语言用 Arial 字体渲染。

---

## 七、安全说明

- **绝不提交真实凭证**：`resources/config.json`、`.env`、cookie、token 均已被 `.gitignore` 忽略；
  仓库只保留 `config.json.example` 占位模板。
- 脚本设计上不打印 `AppSecret`、签名头或含凭证的请求体。
- 发布、认领等为高影响写操作，技能要求显式确认后执行。

## 八、免责声明

- 本项目为**非官方**社区工具，与妙手 ERP、TikTok/字节跳动无隶属关系；接口以妙手开放平台官方
  文档为准，接口变更可能导致脚本失效。
- 尺码表、定价费率、类目属性等为通用参考，**不构成经营/合规/法律建议**；上架前请自行核验商品
  合规性、知识产权与目标站点规则。
- 项目按 MIT 许可证提供，作者不对因使用本工具造成的任何损失负责。
