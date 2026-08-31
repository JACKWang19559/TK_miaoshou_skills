# 尺码表预设、图床选型与必填属性排查

本文件沉淀「妙手 TikTok 服装采集箱发布就绪」闭环中的实测结论与规范，
配合 `scripts/` 下三个脚本使用。

## 一、图床选型（实测）

开放平台的尺码表等图片字段只接受公网 URL，妙手保存时会拉取并转存到
自有 CDN。本机网络实测：

| 图床 | 地址 | 结果 | 说明 |
|---|---|---|---|
| litterbox | `litter.catbox.moe` | ✅ 可用 | catbox 临时托管，免 key，默认 72h，本环境可达 |
| catbox | `catbox.moe` | ⚠️ 不稳定 | 永久链接免 key，但主站在部分网络/地区不可达 |
| 0x0.st | `0x0.st` | ❌ 关停 | 2025 年起已停止匿名上传 |
| sm.ms | `sm.ms` | ❌ 需 token | 匿名上传受限，需账号 API token |

结论：默认用 `upload_image.py`（litterbox 主用、catbox 回退）。

**临时链接注意事项**
- litterbox 链接 72h 后失效；务必在有效期内发布，发布时平台转存 CDN 后即长期有效。
- 若需长期不发布也不失效，用 `--host catbox`（永久）或上传到自建 OSS/COS。
- 平台校验图片格式：URL 必须以 `.jpg/.jpeg/.png/.webp` 结尾或返回对应 Content-Type。

## 二、尺码表设计规范

- **语言**：必须用目标站点语言。越南站用越南语（`--site VN` 预设）。
- **单位**：服装一律 cm，平铺测量；脚注注明手工误差 1–3cm。
- **女装针织上衣参考列**：Size / 胸围(Vòng ngực) / 衣长(Dài áo) /
  肩宽(Rộng vai) / 袖长(Dài tay)。
- **尺码行**：S–3XL 为越南女装常见档；数据为亚洲版型通用参考值，
  非货源实测。若工厂提供真实尺寸，用 `--data` 传自定义 JSON 覆盖。
- **字体**：越南语带变音符号，用 Windows 自带 Arial（`arial.ttf` /
  `arialbd.ttf`），勿用宋体/黑体（缺拉丁扩展字形）。
- 自定义 JSON 字段：`title / subtitle / headers / col_w / rows / notes / accent`。

## 三、必填属性排查（报错驱动 + 元数据确认）

服装类目保存常被必填商品属性拦截（如越南站 cid 601284 必填「材质」）。
排查顺序：

1. **先看 save 报错**：错误文案直接点名缺失项，如
   `产品属性【材质】必填，请填写后重试`。
2. **拉类目属性元数据**：用 category-recommend 技能的 attributes 命令
   （`get_category_attributes`，传 cid + site），筛 `必填:1` /
   `isRequired=true` 的属性，记录 `attributeId`。
3. **取合法 valueId**：在该属性的 `values[]` / 候选值里选与货源一致的
   枚举值，记录 `valueId` 与 `valueName`。多选取货源标注的全部成分。
4. **忠实货源**：材质等属性按 1688 货源标注填写（如「面料名称=氨纶」→
   氨纶 valueId），不要臆造主体面料；平台保存后会把 valueName 本地化为
   站点语言（如氨纶→Elastan）。
5. **非必填不硬填**：制造商/责任人/EPR 仅欧盟站点强制，越南站
   `必填:0`，留空不影响发布。

属性简化 JSON（传给 `build_edit_payload.py --attributes-file`）：

```json
[
  {
    "attributeId": "100157",
    "attributeName": "材质",
    "values": [
      {"valueId": "1001112", "valueName": "氨纶"}
    ]
  }
]
```

## 四、乐观锁与整包回写要点

- **ossMd5 乐观锁**：每次 `detail` 返回的 `ossMd5` 是版本号，`save` 必须
  原样回传；保存成功后返回新 ossMd5，下次编辑用新值。
- **整包回写**：save 的 `--file` 必须是完整 `shopCollectItemInfo` 对象
  （本技能 `build_edit_payload.py` 深拷贝生成），不能只传改动片段，
  否则标题/描述/图片/规格会被抹掉。
- **SKU 遍历**：跳过 `isDelete=1` 的 SKU；改 price/stock/weight 时同步
  更新 `shopIdToWarehouseIdAndStockMap` 多仓库存（值为字符串）。
- **价格双字段（越南站实测坑）**：SKU 同时有 `price` 与 `priceIncludeVat`。
  越南站前台「零售价」取 **`priceIncludeVat`（含税价）**；该值在采集/认领时
  由系统按货源价 `originPrice` 自动算成高溢价建议价。**只改 `price` 不改
  `priceIncludeVat`，上架后前台仍显示系统高价**。改价务必两个字段都写成
  目标售价（目标售价即买家实付含税价）。库存/重量正确不代表价格正确，发布后
  必须到 TikTok 卖家中心核对前台零售价。
- **发布后无法用妙手 API 改在线价**：publish 技能只有采集箱（发布前）端点，
  没有「在线商品改价」接口。商品一旦发布，在线 listing 价格只能在 TikTok
  卖家中心改；采集箱里改不会回写已发布商品。因此价格务必在发布前于采集箱
  核对 `priceIncludeVat` 正确。
- **保存后验证**：重新 `detail` 拉取，核对 price/stock/weight/尺寸/
  sizeChart/productAttributes 落库，再跑 `diagnose` 确认「可发布」。
