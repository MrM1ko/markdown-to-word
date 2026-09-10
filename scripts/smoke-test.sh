#!/bin/sh
set -eu

root=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/markdown-to-word-smoke.XXXXXX")
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM

input="$tmp_dir/示例 input.md"
output="$tmp_dir/示例 output.docx"

cat >"$input" <<'EOF'
# 中英文转换测试

这是中文正文，包含 English text 和数字 2026。

- 列表项目一
- List item two
EOF

"$root/scripts/convert.sh" "$input" "$output" >/dev/null
test -s "$output"
unzip -t "$output" >/dev/null
unzip -p "$output" word/document.xml | grep -q '中英文转换测试'
unzip -p "$output" word/styles.xml | grep -q '宋体'
unzip -p "$output" word/styles.xml | grep -q '黑体'
unzip -p "$output" word/styles.xml | grep -q 'Times New Roman'

printf 'PASS: %s\n' "$output"
