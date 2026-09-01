---
name: "miaoshou-erp-tiktok-apparel-readiness"
description: "Complete Miaoshou ERP TikTok apparel collect-box required fields for publishing: generate a localized size-chart image, host it to a public URL, fill required category attributes (e.g. material), set package dimensions/weight and SKU price/stock, then save and verify. Invoke when a TikTok clothing/garment product save is blocked by a missing size chart or required attributes, or when the user asks to 补齐尺码表/材质属性/发布硬伤/服装上架就绪."
---

# 妙手 TikTok 服装采集箱发布就绪

把妙手 ERP 采集箱里的 TikTok **服装类目**商品补齐到「可发布」状态。服装类目
有两个高频强制拦截项——**尺码表**（只接受公网图片 URL）和**必填商品属性**
（如越南站「材质」），本技能闭环解决：生成本地化尺码表图 → 公网托管 →
解析并填入必填属性 → 整包改价/库存/物流 → 保存 → 验证。

依赖与协同：
- 商品详情/保存/诊断复用 `miaoshou-erp-tiktok-product-edit` 技能的
  `scripts/tiktok_collectbox.py`（detail / save / diagnose）。
- 类目属性元数据复用 `miaoshou-erp-tiktok-category-recommend` 技能
  （attributes / get_category_attributes）。
- 本技能提供三个脚本，见 `scripts/`；实测结论见
  `references/sizechart-and-attributes.md`。

## 触发场景

- save 报错 `请上传尺码图` / `尺码表图片URL仅支持...格式`。
- save 报错 `产品属性【材质/xxx】必填，请填写后重试`。
- 用户说「补齐尺码表」「补齐发布硬伤」「服装上架就绪」「尺寸/重量/价格库存
  还没填」。

## 标准工作流

脚本均在本技能 `scripts/` 目录；下文 `$SKILL` 指本技能目录，
`$EDIT` 指 `miaoshou-erp-tiktok-product-edit` 技能目录。所有 Python 命令
以 `py` 开头，加 `-X utf8`。

### 1. 拉详情 + 诊断，拿 ossMd5

```powershell
py -X utf8 "$EDIT\scripts\tiktok_collectbox.py" --output detail.json detail <detailId> --mode shop --shop-id <shopId> --site VN
py -X utf8 "$EDIT\scripts\tiktok_collectbox.py" diagnose <detailId> --mode shop --shop-id <shopId> --site VN
```

记录详情里的 `ossMd5`（乐观锁版本号，save 必须回传）。diagnose 列出
缺失项；尺码表、类目属性、重量尺寸是服装高频硬伤。

### 2. 生成并托管尺码表（服装必填）

```powershell
# 用站点语言预设生成（内置越南语女装上衣 S-3XL）
py -X utf8 "$SKILL\scripts\gen_sizechart.py" --site VN --out sizechart.png
# 工厂有真实尺寸时用自定义 JSON：--data my_sizes.json
# 均码商品（SKU 只有单一尺码）勿用 S-3XL 预设，须用 --data 生成单行
# Freesize 表（列 Size / Dài áo / Cân nặng），见 references 第二节

# 上传公网图床拿直链（stdout 只输出 URL；litterbox 默认 72h）
py -X utf8 "$SKILL\scripts\upload_image.py" sizechart.png
# 图床被拦截（litterbox 500 / catbox 412 / telegra.ph 400）时，用 GitHub raw 兜底：
py -X utf8 "$SKILL\scripts\push_github_raw.py" sizechart.png --repo <git仓库路径> --rel assets/sizechart.png
```

把输出的 URL 填入下一步 `--size-chart-url`。临时链接 72h 失效，需在
有效期内发布；要长期链接加 `--host catbox` 或走 GitHub raw（永久）。
GitHub raw 依赖已配置可推送的 git 仓库，脚本自动从 origin 推导 raw 前缀。

### 3. 查必填商品属性（报错驱动）

- 若 save 报「【材质】必填」等，用 category-recommend 的 attributes 命令
  拉 `<cid>` + site 的类目属性元数据，筛 `必填:1` 的属性，记录
  `attributeId`；在其候选值里选与 **1688 货源标注一致** 的枚举值，记录
  `valueId`/`valueName`。
- 写成简化属性 JSON 文件 `attrs.json`（格式见
  `references/sizechart-and-attributes.md` 第三节）。多选取货源标注的全部
  成分，不要臆造主体面料。

### 4. 构建 edit.json（深拷贝整包，只改目标字段）

```powershell
py -X utf8 "$SKILL\scripts\build_edit_payload.py" `
  --detail detail.json --out edit.json `
  --price 299000 --stock 555 --weight 0.4 `
  --length 30 --width 25 --height 3 `
  --size-chart-url "<第2步URL>" `
  --attributes-file attrs.json
```

脚本深拷贝 `shopCollectItemInfo`，标题/描述/图片/规格/类目等原样保留；
遍历有效 SKU 改 price/stock/weight 并同步多仓库存。所有改值字段可选，
不传则不动。

### 5. 保存（回传 ossMd5）

```powershell
py -X utf8 "$EDIT\scripts\tiktok_collectbox.py" save <detailId> `
  --mode shop --shop-id <shopId> --site VN `
  --oss-md5 "<第1步 ossMd5>" --file edit.json
```

- 成功会返回**新 ossMd5**，记录供下次编辑。
- 若再报必填项（新属性/新字段），回第 3 步补属性后重建 payload 重存；
  每次重存前若详情可能被改动，重新 detail 拿最新 ossMd5。

### 6. 验证

```powershell
py -X utf8 "$EDIT\scripts\tiktok_collectbox.py" --output verify.json detail <detailId> --mode shop --shop-id <shopId> --site VN
py -X utf8 "$EDIT\scripts\tiktok_collectbox.py" diagnose <detailId> --mode shop --shop-id <shopId> --site VN
```

核对 verify.json：各 SKU `price/stock/weight`、包裹尺寸、`sizeChartType=
image`+URL、`productAttributes` 落库；diagnose 结论为「可发布」。
制造商/责任人仅欧盟站点强制，越南站可留空。

### 7. 交接发布

达到可发布后，交 `miaoshou-erp-tiktok-product-publish` 技能执行发布。
提醒用户：临时尺码图在发布时会被平台转存 CDN，务必在图床有效期内发布。

## 注意事项

- 尺码数据为通用参考值，非货源实测；有工厂尺寸务必用 `--data` 覆盖。
- 尺码表语言必须匹配站点（越南站用越南语），字体用 Arial 以支持变音符号。
- 均码商品（单一尺码 SKU）用 `--data` 生成单行 Freesize 表，勿套 S–3XL。
- 图床不可达时用 `push_github_raw.py` 走 GitHub raw 兜底（永久、海外可达）。
- 属性多选限制：未标「可多选」的属性（如「设计」100406）只能填一个值，
  多填报 `产品属性【设计】不支持多选`，只保留主打元素。
- 不在技能脚本里硬编码任何 detailId/shopId/ossMd5/图床 URL/属性 ID——
  这些都是任务数据，每次运行时实时获取。
- 临时脚本与中间 JSON 放工作临时目录，技能目录只保留可复用脚本与文档。
