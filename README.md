# 小说下载器

一个支持图形界面和命令行的 Python 小说下载工具，专为 qb5.io 等小说网站设计。
通过"下一页"导航突破反爬虫限制，自动下载全部章节并生成 EPUB / TXT 文件。

## 功能特点

- ✅ **图形界面** — Tkinter GUI，操作直观
- ✅ **智能导航下载** — 从第一章开始，沿正文"下一页"按钮逐章遍历，突破目录页反爬限制
- ✅ **暂停 / 继续 / 终止** — 暂停时保存已下载内容，终止时自动清理临时文件
- ✅ **双格式输出** — 同时或单独生成 EPUB（带目录导航）和 TXT 文件
- ✅ **自动去广告** — 过滤常见广告词和无关内容
- ✅ **CLI 模式** — 支持命令行参数，适合脚本化使用
- ✅ **Selenium 增强** — 自动检测并点击"展开列表"等按钮，获取隐藏章节

## 安装依赖

```bash
pip install -r requirements.txt
```

如需 Selenium 增强功能（Edge 或 Chrome 浏览器），还需安装：
```bash
pip install selenium webdriver-manager
```

## 使用方法

### 图形界面（推荐）

双击 `download_novel.bat` 或在终端运行：

```bash
python novel_downloader_gui.py
```

在界面中输入小说主页 URL → 选择输出格式 → 点"开始下载"

支持按钮：
| 按钮 | 说明 |
|------|------|
| 开始下载 | 启动下载 |
| 暂停下载 | 暂停并保存 `_partial.txt` 供查看 |
| 继续下载 | 从暂停处恢复 |
| 终止下载 | 终止任务并删除临时文件 |

### 命令行

```bash
# 下载并同时生成 EPUB + TXT（默认）
python novel_downloader.py https://www.qb5.io/xs-66401/

# 只生成 EPUB
python novel_downloader.py https://www.qb5.io/xs-66401/ -f epub

# 指定输出文件名
python novel_downloader.py https://www.qb5.io/xs-66401/ -f both -o "花间骄子"
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `url` | 小说主页 URL（必需） |
| `-f, --format` | 输出格式：`epub`、`txt`、`both`（默认） |
| `-o, --output` | 输出文件名（不含扩展名），默认使用小说标题 |

## 技术实现

1. **目录页解析** — 获取小说标题、作者、初始章节列表（可选 Selenium 展开）
2. **正文导航下载** — 从第一章进入，提取标题 → 下载正文（含同章分页） → 找"下一页" → 循环
3. **正文去重** — 自动去除正文开头重复的章节标题
4. **文件保存** — TXT 仅正文内容；EPUB 包含完整目录结构

## 注意事项

- 下载过程有 0.8s 延时，避免请求过快被封
- 暂停生成的 `_partial.txt` 仅供临时查看，完成下载后自动删除
- Windows 系统建议使用 Edge 浏览器（无需额外安装驱动）
- 如遇到"下一页"无法识别，可在 issue 中提供示例 URL

