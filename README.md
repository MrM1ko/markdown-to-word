# markdown-to-word

一个最小、可复现的 Codex Skill：用 Pandoc 和固定 `reference.docx` 将 Markdown 转换为排版稳定的 Word。

## 功能

- 正文中文使用宋体，标题中文使用黑体且不加粗；英文和数字使用 `Times New Roman`。
- A4、上下页边距 2.54 cm、左右页边距 3.18 cm、1.5 倍行距。
- 正文首行缩进两字符。
- 不添加 `keepNext`、`keepLines`、`pageBreakBefore` 或 `widowControl`。
- 从 Markdown 所在目录解析相对图片等资源。

## 环境

- Pandoc 3.x
- Codex（作为 Skill 使用时）
- LibreOffice 或 Microsoft Word（用于最终页面检查）
- Python 3.9+（仅重建 `reference.docx` 时需要）

macOS 可安装 Pandoc：

```bash
brew install pandoc
```

## 安装为 Codex Skill

把本仓库放到：

```text
~/.codex/skills/markdown-to-word
```

例如：

```bash
cp -R /path/to/markdown-to-word ~/.codex/skills/markdown-to-word
```

新开 Codex 任务后调用：

```text
$markdown-to-word 把 /path/to/input.md 转成 Word
```

## 直接使用

```bash
scripts/convert.sh INPUT.md [OUTPUT.docx]
```

未指定输出路径时，会在 Markdown 旁边生成同名 `.docx`。

## 修改排版

排版参数集中在 `scripts/build_reference.py` 顶部。修改字体、字号、页边距或标题间距后执行：

```bash
python3 scripts/build_reference.py
```

该命令会从当前 Pandoc 提取官方默认模板，重新生成 `assets/reference.docx`；失败时不会覆盖原模板。

## 检查

```bash
scripts/smoke-test.sh
```

冒烟测试会在临时目录执行一次中英文 Markdown 转换，并检查 DOCX 压缩包、正文和模板字体。正式交付前仍应将结果渲染为页面图片并逐页检查。

## 结构

```text
SKILL.md                    Agent 入口指令
agents/openai.yaml          Codex 界面元数据
assets/reference.docx       Pandoc Word 样式模板
scripts/convert.sh          Markdown 转 DOCX
scripts/build_reference.py  可复现模板生成器
scripts/smoke-test.sh       最小可运行检查
LICENSES/                   Pandoc 许可证
```

## 许可证说明

`assets/reference.docx` 基于 Pandoc 随附的默认参考文档生成。Pandoc 的许可证文本位于 `LICENSES/pandoc-COPYING.md`。本仓库尚未为其余原创文件指定单独的开源许可证。
