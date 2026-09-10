#!/bin/sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: $0 INPUT.md [OUTPUT.docx]" >&2
  exit 2
fi

input=$1
output=${2:-${input%.*}.docx}

if [ ! -f "$input" ]; then
  echo "Input Markdown not found: $input" >&2
  exit 1
fi

case "$input" in
  /*) input_abs=$input ;;
  *) input_abs=$(pwd -P)/$input ;;
esac
case "$output" in
  /*) output_abs=$output ;;
  *) output_abs=$(pwd -P)/$output ;;
esac
case "$output_abs" in
  *.docx) ;;
  *) echo "Output must end in .docx: $output_abs" >&2; exit 2 ;;
esac

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
input_dir=$(CDPATH= cd "$(dirname "$input_abs")" && pwd -P)
reference=$script_dir/../assets/reference.docx
pandoc_bin=${PANDOC:-pandoc}

command -v "$pandoc_bin" >/dev/null 2>&1 || {
  echo "Pandoc is required: https://pandoc.org/installing.html" >&2
  exit 127
}
[ -f "$reference" ] || { echo "Missing reference document: $reference" >&2; exit 1; }

mkdir -p "$(dirname "$output_abs")"
"$pandoc_bin" \
  --from=markdown \
  --to=docx \
  --standalone \
  --reference-doc="$reference" \
  --resource-path="$input_dir" \
  --output="$output_abs" \
  "$input_abs"

printf '%s\n' "$output_abs"
