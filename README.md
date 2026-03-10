# 小说下载器

一个用于下载小说并转换为EPUB或TXT格式的Python脚本。

## 功能特点

- ✅ 自动获取章节列表
- ✅ 下载所有章节内容
- ✅ 自动去除广告和无关内容
- ✅ 生成带目录的EPUB和TXT文件
- ✅ 支持自定义输出格式

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
# 下载小说并同时生成EPUB和TXT格式（默认）
python novel_downloader.py https://www.qb5.io/xs-66401/

# 只生成EPUB格式
python novel_downloader.py https://www.qb5.io/xs-66401/ -f epub

# 只生成TXT格式
python novel_downloader.py https://www.qb5.io/xs-66401/ -f txt

# 指定输出文件名
python novel_downloader.py https://www.qb5.io/xs-66401/ -o "花间骄子"
```

### 参数说明

- `url`: 小说主页URL（必需）
- `-f, --format`: 输出格式，可选值：`epub`、`txt`、`both`（默认：`both`）
- `-o, --output`: 输出文件名（不含扩展名），如果不指定则使用小说标题

## 示例

```bash
# 下载《花间骄子》并生成两种格式
python novel_downloader.py https://www.qb5.io/xs-66401/

# 只生成EPUB格式，文件名为"花间骄子"
python novel_downloader.py https://www.qb5.io/xs-66401/ -f epub -o "花间骄子"
```

## 注意事项

1. 脚本会自动去除常见的广告内容
2. 下载过程中会有适当的延迟，避免请求过快
3. 如果某个章节下载失败，会在文件中标记为"[此章节内容获取失败]"
4. 生成的EPUB文件包含完整的目录结构，可以在电子书阅读器中正常使用

