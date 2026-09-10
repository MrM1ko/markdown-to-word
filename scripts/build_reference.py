#!/usr/bin/env python3
"""Rebuild assets/reference.docx from Pandoc's bundled default template."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional, Tuple


CN_FONT = "宋体"
HEADING_FONT = "黑体"
EN_FONT = "Times New Roman"
CODE_FONT = "Consolas"

BODY_SIZE = 24       # half-points: 12 pt
TITLE_SIZE = 44      # 22 pt
HEADING_1_SIZE = 32  # 16 pt
HEADING_2_SIZE = 28  # 14 pt
HEADING_3_SIZE = 24  # 12 pt
CAPTION_SIZE = 21    # 10.5 pt
FOOTNOTE_SIZE = 18   # 9 pt
CODE_SIZE = 20       # 10 pt

PAGE_WIDTH = 11906   # A4, twips
PAGE_HEIGHT = 16838
PAGE_MARGIN = 1440   # top/bottom: 25.4 mm
SIDE_MARGIN = 1803   # left/right: 31.8 mm, rounded to twips
HEADER_FOOTER = 720  # 12.7 mm

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W}
ET.register_namespace("w", W)
ET.register_namespace("r", R)


def q(name: str) -> str:
    return f"{{{W}}}{name}"


def child(parent: ET.Element, name: str) -> ET.Element:
    node = parent.find(f"w:{name}", NS)
    return node if node is not None else ET.SubElement(parent, q(name))


def remove_tags(root: ET.Element, names: tuple[str, ...]) -> None:
    tags = {q(name) for name in names}
    for parent in root.iter():
        for node in list(parent):
            if node.tag in tags:
                parent.remove(node)


def set_fonts(rpr: ET.Element, latin: str = EN_FONT) -> None:
    fonts = child(rpr, "rFonts")
    fonts.attrib.clear()
    for key, value in (("ascii", latin), ("hAnsi", latin), ("eastAsia", CN_FONT), ("cs", latin)):
        fonts.set(q(key), value)


def set_size(rpr: ET.Element, half_points: int) -> None:
    child(rpr, "sz").set(q("val"), str(half_points))
    child(rpr, "szCs").set(q("val"), str(half_points))


def set_not_bold(rpr: ET.Element) -> None:
    child(rpr, "b").set(q("val"), "0")
    child(rpr, "bCs").set(q("val"), "0")


def set_black(rpr: ET.Element) -> None:
    color = child(rpr, "color")
    color.attrib.clear()
    color.set(q("val"), "000000")


def set_spacing(ppr: ET.Element, before: int = 0, after: int = 0) -> None:
    spacing = child(ppr, "spacing")
    spacing.attrib.clear()
    for key, value in (("before", before), ("after", after), ("line", 360)):
        spacing.set(q(key), str(value))
    spacing.set(q("lineRule"), "auto")


def set_first_line_chars(ppr: ET.Element, value: int) -> None:
    indent = child(ppr, "ind")
    for name in ("firstLine", "hanging", "hangingChars"):
        indent.attrib.pop(q(name), None)
    indent.set(q("firstLineChars"), str(value))


def style(root: ET.Element, style_id: str) -> Optional[ET.Element]:
    return root.find(f"w:style[@w:styleId='{style_id}']", NS)


def style_parts(root: ET.Element, style_id: str) -> Optional[Tuple[ET.Element, ET.Element]]:
    node = style(root, style_id)
    return None if node is None else (child(node, "pPr"), child(node, "rPr"))


def patch_styles(data: bytes) -> bytes:
    root = ET.fromstring(data)
    remove_tags(root, ("keepNext", "keepLines", "pageBreakBefore", "widowControl"))

    defaults_rpr = root.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
    defaults_ppr = root.find("w:docDefaults/w:pPrDefault/w:pPr", NS)
    if defaults_rpr is None or defaults_ppr is None:
        raise RuntimeError("Pandoc reference.docx is missing expected defaults")
    set_fonts(defaults_rpr)
    set_size(defaults_rpr, BODY_SIZE)
    set_spacing(defaults_ppr)

    for node in root.findall("w:style", NS):
        if node.get(q("type")) in {"paragraph", "character"}:
            set_fonts(child(node, "rPr"), CODE_FONT if node.get(q("styleId")) == "VerbatimChar" else EN_FONT)

    for style_id in ("BodyText", "FirstParagraph", "Abstract"):
        parts = style_parts(root, style_id)
        if parts:
            ppr, rpr = parts
            set_spacing(ppr)
            set_first_line_chars(ppr, 200)
            set_size(rpr, BODY_SIZE)

    for style_id in ("Normal", "Compact", "Bibliography", "Definition", "DefinitionTerm"):
        parts = style_parts(root, style_id)
        if parts:
            ppr, rpr = parts
            set_spacing(ppr)
            set_first_line_chars(ppr, 0)
            set_size(rpr, BODY_SIZE)

    for style_id, size in (("Title", TITLE_SIZE), ("Subtitle", HEADING_2_SIZE), ("Author", BODY_SIZE), ("Date", BODY_SIZE)):
        parts = style_parts(root, style_id)
        if parts:
            ppr, rpr = parts
            set_spacing(ppr, after=120)
            set_first_line_chars(ppr, 0)
            set_size(rpr, size)
            set_black(rpr)
            if style_id == "Title":
                set_not_bold(rpr)

    heading_sizes = {1: HEADING_1_SIZE, 2: HEADING_2_SIZE}
    for level in range(1, 10):
        parts = style_parts(root, f"Heading{level}")
        if not parts:
            continue
        ppr, rpr = parts
        before, after = (240, 120) if level == 1 else (180, 80) if level == 2 else (120, 60)
        set_spacing(ppr, before, after)
        set_first_line_chars(ppr, 0)
        set_size(rpr, heading_sizes.get(level, HEADING_3_SIZE))
        set_not_bold(rpr)
        set_black(rpr)
        for name in ("i", "iCs"):
            node = rpr.find(f"w:{name}", NS)
            if node is not None:
                rpr.remove(node)

    for level in range(1, 10):
        node = style(root, f"Heading{level}Char")
        if node is not None:
            rpr = child(node, "rPr")
            set_size(rpr, heading_sizes.get(level, HEADING_3_SIZE))
            set_not_bold(rpr)
            set_black(rpr)
            for name in ("i", "iCs"):
                italic = rpr.find(f"w:{name}", NS)
                if italic is not None:
                    rpr.remove(italic)

    for style_id in ("BlockText", "FootnoteBlockText"):
        parts = style_parts(root, style_id)
        if parts:
            ppr, _ = parts
            set_spacing(ppr)
            set_first_line_chars(ppr, 0)

    for style_id in ("Caption", "TableCaption", "ImageCaption", "Figure", "CaptionedFigure"):
        parts = style_parts(root, style_id)
        if parts:
            ppr, rpr = parts
            set_spacing(ppr, after=120)
            set_first_line_chars(ppr, 0)
            set_size(rpr, CAPTION_SIZE)

    parts = style_parts(root, "FootnoteText")
    if parts:
        ppr, rpr = parts
        set_spacing(ppr)
        set_first_line_chars(ppr, 0)
        set_size(rpr, FOOTNOTE_SIZE)

    verbatim = style(root, "VerbatimChar")
    if verbatim is not None:
        set_size(child(verbatim, "rPr"), CODE_SIZE)

    for node in root.findall("w:style", NS):
        style_id = node.get(q("styleId"), "")
        if node.get(q("type")) == "paragraph":
            spacing = child(child(node, "pPr"), "spacing")
            spacing.set(q("line"), "360")
            spacing.set(q("lineRule"), "auto")
        if style_id.startswith("Heading") or style_id in {
            "Title", "TitleChar", "Subtitle", "SubtitleChar", "AbstractTitle", "TOCHeading"
        }:
            rpr = child(node, "rPr")
            child(rpr, "rFonts").set(q("eastAsia"), HEADING_FONT)
            set_not_bold(rpr)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def patch_document(data: bytes) -> bytes:
    root = ET.fromstring(data)
    remove_tags(root, ("keepNext", "keepLines", "pageBreakBefore", "widowControl"))
    section = root.find(".//w:sectPr", NS)
    if section is None:
        raise RuntimeError("Pandoc reference.docx is missing section properties")
    page = child(section, "pgSz")
    page.set(q("w"), str(PAGE_WIDTH))
    page.set(q("h"), str(PAGE_HEIGHT))
    margin = child(section, "pgMar")
    for name in ("top", "right", "bottom", "left"):
        margin.set(q(name), str(SIDE_MARGIN if name in {"left", "right"} else PAGE_MARGIN))
    margin.set(q("header"), str(HEADER_FOOTER))
    margin.set(q("footer"), str(HEADER_FOOTER))
    margin.set(q("gutter"), "0")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def patch_font_table(data: bytes) -> bytes:
    root = ET.fromstring(data)
    existing = {node.get(q("name")) for node in root.findall("w:font", NS)}
    for name in (EN_FONT, CN_FONT, HEADING_FONT, CODE_FONT):
        if name not in existing:
            ET.SubElement(root, q("font"), {q("name"): name})
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def patch_archive(path: Path) -> None:
    patches = {
        "word/styles.xml": patch_styles,
        "word/document.xml": patch_document,
        "word/fontTable.xml": patch_font_table,
    }
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".docx", delete=False) as handle:
        rebuilt = Path(handle.name)
    try:
        with zipfile.ZipFile(path) as source, zipfile.ZipFile(rebuilt, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                target.writestr(info, patches.get(info.filename, lambda value: value)(data))
        os.replace(rebuilt, path)
    finally:
        rebuilt.unlink(missing_ok=True)


def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit(f"Usage: {Path(sys.argv[0]).name} [OUTPUT.docx]")
    root = Path(__file__).resolve().parent.parent
    output = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else root / "assets/reference.docx"
    pandoc = os.environ.get("PANDOC", "pandoc")
    if shutil.which(pandoc) is None:
        raise SystemExit("Pandoc is required: https://pandoc.org/installing.html")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".docx", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        subprocess.run([pandoc, "-o", str(temporary), "--print-default-data-file", "reference.docx"], check=True)
        patch_archive(temporary)
        os.replace(temporary, output)
        output.chmod(0o644)
    finally:
        temporary.unlink(missing_ok=True)
    print(output)


if __name__ == "__main__":
    main()
