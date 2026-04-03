# Scripts

## process.py（核心脚本）

批量处理微信聊天截图：自动检测敏感区域 → OCR 提取文字 → NER 识别人名/公司名 → 打马赛克。

```bash
python3 process.py /path/to/screenshots --output-dir /path/to/output
```

输出：
- 打码后的图片
- `_summary.json`：处理摘要，含 OCR 文本、对话分组、打码区域列表

依赖：Pillow, cnocr, onnxruntime, jieba

## detect.py

检测微信截图中的特定区域：
- `find_title_region(img)` — 检测导航栏标题区域
- `find_left_avatars(img, content_start)` — 检测左侧头像区域

```bash
python3 detect.py <image_path>
# 输出 JSON 格式的检测结果
```

依赖：Pillow

## mosaic.py

对图片指定区域应用马赛克（像素化）。

```bash
python3 mosaic.py <input> <output> '<regions_json>'
```

参数：
- `regions_json`：JSON 数组，每个元素包含 `x`, `y`, `w`, `h`，可选 `block_size`

```bash
python3 mosaic.py chat.png out.png '[{"x":10,"y":50,"w":45,"h":45}]'
```

依赖：Pillow
