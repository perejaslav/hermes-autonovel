#!/usr/bin/env python3
"""
Build a valid EPUB3 from individual chapter .md files.

Key design decisions:
- pandoc generates raw HTML fragments (no --standalone, no inline CSS)
- We strip any <style> blocks pandoc injects
- Each chapter is wrapped in a clean XHTML shell that links epub_style.css
- EPUB structure: mimetype (uncompressed), META-INF/container.xml,
  EPUB/content.opf (manifest+spine), EPUB/nav.xhtml, EPUB/toc.ncx,
  EPUB/styles/epub_style.css, EPUB/text/ch_*.xhtml

Expected layout:
  epub_build/          ← .md source files (one per chapter)
  epub_out/            ← pandoc HTML output (created here, then cleaned)
  EPUB/text/           ← final chapter XHTML (created here)
  epub_style.css       ← stylesheet source (copied to EPUB/)
  the_speaking_tide.epub ← final output

Usage:
  python build_epub.py --title "My Novel" --author "Me"
"""

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
BUILD_DIR = ROOT / "epub_build"
OUT_DIR = ROOT / "epub_out"
EPUB_DIR = ROOT / "EPUB"
EPUB_TEXT_DIR = EPUB_DIR / "text"
EPUB_STYLES_DIR = EPUB_DIR / "styles"
EPUB_META_DIR = ROOT / "META-INF"


def natural_sort_key(s: str):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]


def collect_chapters(build_dir: Path) -> list[Path]:
    return sorted(build_dir.glob("ch_*.md"), key=lambda p: natural_sort_key(p.name))


def convert_markdown_to_clean_xhtml(md_path: Path, out_path: Path, title: str):
    """
    Convert .md to XHTML via pandoc, strip any inline <style> blocks,
    and wrap in a minimal XHTML shell that references epub_style.css.
    """
    # Run pandoc WITHOUT --standalone and WITHOUT --css (both inject inline cruft)
    cmd = [
        "pandoc",
        str(md_path),
        "-o", str(out_path),
        "--from=markdown",
        "--to=html5",
        "--metadata", f"pagetitle={title}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR converting {md_path.name}: {result.stderr}", file=sys.stderr)
        raise RuntimeError(result.stderr)

    # Read the raw pandoc output
    html = out_path.read_text(encoding="utf-8")

    # Strip any <style>...</style> blocks pandoc may have injected
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

    # Also strip any inline width="" or style="max-width" on body (from pandoc)
    html = re.sub(r'<body([^>]*)>', '<body>', html)

    # Wrap in a proper XHTML5 shell
    xhtml_content = XHTML_SHELL.format(
        title=title,
        body_content=html.strip(),
        css_href="styles/epub_style.css",
    )
    out_path.write_text(xhtml_content, encoding="utf-8")
    print(f"  {md_path.name} → {out_path.name}")


def build_epub(args):
    title = args.title
    author = args.author
    epub_filename = args.output or f"{title.lower().replace(' ', '_')}.epub"

    print(f"Building EPUB: '{title}' by {author}")

    # ── 1. Setup directories ────────────────────────────────────────────────
    for d in (OUT_DIR, EPUB_TEXT_DIR, EPUB_STYLES_DIR, EPUB_META_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # ── 2. Convert markdown → clean XHTML ──────────────────────────────────
    print("\n[1/5] Converting markdown → XHTML (stripping pandoc inline styles)...")
    chapters = collect_chapters(BUILD_DIR)
    if not chapters:
        print(f"ERROR: No chapter files found in {BUILD_DIR}", file=sys.stderr)
        sys.exit(1)

    for md_path in chapters:
        ch_num = re.search(r'ch_(\d+)', md_path.name).group(1)
        xhtml_name = f"ch_{ch_num}.xhtml"
        xhtml_path = OUT_DIR / xhtml_name
        convert_markdown_to_clean_xhtml(md_path, xhtml_path, f"Chapter {ch_num}")

    # ── 3. Front/back matter ───────────────────────────────────────────────
    print("\n[2/5] Converting front/back matter...")
    for md_name, xhtml_name in [
        ("epub_front_matter.md", "front_matter.xhtml"),
        ("epub_back_cover.md", "back_cover.xhtml"),
        ("epub_colophon.md", "colophon.xhtml"),
    ]:
        md_path = ROOT / md_name
        if md_path.exists():
            xhtml_path = OUT_DIR / xhtml_name
            convert_markdown_to_clean_xhtml(md_path, xhtml_path, title)

    # Copy stylesheet to EPUB/
    style_src = ROOT / "epub_style.css"
    if style_src.exists():
        shutil.copy(style_src, EPUB_STYLES_DIR / "epub_style.css")

    # ── 4. Build content.opf ───────────────────────────────────────────────
    print("\n[3/5] Building content.opf...")
    all_xhtml = sorted(OUT_DIR.glob("*.xhtml"), key=lambda p: natural_sort_key(p.name))

    manifest_items = []
    spine_items = []

    def add_manifest_and_spine(item_id, href, in_spine=True):
        manifest_items.append(
            f'    <item id="{item_id}" href="{href}" media-type="application/xhtml+xml"/>'
        )
        if in_spine:
            spine_items.append(f'      <itemref idref="{item_id}"/>')

    # Front matter
    if (OUT_DIR / "front_matter.xhtml").exists():
        add_manifest_and_spine("front_matter", "text/front_matter.xhtml")

    # Chapters
    for xhtml_path in all_xhtml:
        if xhtml_path.name in ("front_matter.xhtml", "back_cover.xhtml", "colophon.xhtml"):
            continue
        chapter_id = xhtml_path.stem  # "ch_01"
        add_manifest_and_spine(chapter_id, f"text/{xhtml_path.name}")

    # Back matter
    if (OUT_DIR / "back_cover.xhtml").exists():
        add_manifest_and_spine("back_cover", "text/back_cover.xhtml")
    if (OUT_DIR / "colophon.xhtml").exists():
        add_manifest_and_spine("colophon", "text/colophon.xhtml")

    # Nav and CSS
    manifest_items.append('    <item id="css" href="styles/epub_style.css" media-type="text/css"/>')
    manifest_items.append('    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
    manifest_items.append('    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')

    opf_path = EPUB_DIR / "content.opf"
    opf_path.write_text(
        OPF_TEMPLATE.format(
            title=title,
            author=author,
            manifest="\n".join(manifest_items),
            spine="\n".join(spine_items),
        ),
        encoding="utf-8",
    )
    print(f"  Written: {opf_path.name}  ({len(spine_items)} spine items)")

    # ── 5. Build navigation documents ───────────────────────────────────────
    print("\n[4/5] Building nav.xhtml and toc.ncx...")

    # nav.xhtml — EPUB3 navigation
    nav_items = []
    for xhtml_path in all_xhtml:
        if xhtml_path.name in ("front_matter.xhtml", "back_cover.xhtml", "colophon.xhtml"):
            continue
        ch_num = re.search(r'ch_(\d+)', xhtml_path.name).group(1)
        nav_items.append(
            f'      <li><a href="text/{xhtml_path.name}">Chapter {ch_num}</a></li>'
        )

    nav_path = EPUB_DIR / "nav.xhtml"
    nav_path.write_text(
        NAV_TEMPLATE.format(title=title, chapters="\n".join(nav_items)),
        encoding="utf-8",
    )

    # toc.ncx — legacy navigation
    ncx_items = []
    for i, xhtml_path in enumerate(all_xhtml, 1):
        if xhtml_path.name in ("front_matter.xhtml", "back_cover.xhtml", "colophon.xhtml"):
            continue
        ch_num = re.search(r'ch_(\d+)', xhtml_path.name).group(1)
        ncx_items.append(
            f"""      <navPoint id="navpoint-{i}" playOrder="{i}">
        <navLabel><text>Chapter {ch_num}</text></navLabel>
        <content src="text/{xhtml_path.name}"/>
      </navPoint>"""
        )

    ncx_path = EPUB_DIR / "toc.ncx"
    ncx_path.write_text(
        NCX_TEMPLATE.format(title=title, uid="nov-001", chapters="\n".join(ncx_items)),
        encoding="utf-8",
    )

    # ── 6. Copy XHTML to EPUB/text/ ─────────────────────────────────────────
    print("\n[5/5] Assembling EPUB archive...")
    for xhtml_path in OUT_DIR.glob("*.xhtml"):
        dest = EPUB_TEXT_DIR / xhtml_path.name
        dest.write_text(xhtml_path.read_text(encoding="utf-8"), encoding="utf-8")

    # ── 7. Write META-INF/container.xml ────────────────────────────────────
    EPUB_META_DIR.joinpath("container.xml").write_text(CONTAINER_TEMPLATE, encoding="utf-8")

    # ── 8. Write mimetype (must be first, uncompressed) ─────────────────────
    mimetype_path = ROOT / "mimetype"
    mimetype_path.write_text("application/epub+zip", encoding="utf-8")

    # ── 9. Zip it all ──────────────────────────────────────────────────────
    epub_path = ROOT / epub_filename
    with zipfile.ZipFile(str(epub_path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(str(mimetype_path), arcname="mimetype", compress_type=zipfile.ZIP_STORED)
        for f in EPUB_DIR.rglob("*"):
            if f.is_file():
                zf.write(str(f), arcname=str(f.relative_to(ROOT)))

    mimetype_path.unlink()

    size_kb = epub_path.stat().st_size // 1024
    print(f"\n✅ EPUB: {epub_path} ({size_kb} KB, {len(all_xhtml)} chapters)")


# ── Templates ────────────────────────────────────────────────────────────────

XHTML_SHELL = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
<head>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="{css_href}"/>
</head>
<body>
{body_content}
</body>
</html>
"""

OPF_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="uid">nov-001</dc:identifier>
    <meta property="dcterms:modified">2026-04-21T00:00:00Z</meta>
  </metadata>
  <manifest>
{manifest}
  </manifest>
  <spine toc="ncx">
{spine}
  </spine>
</package>
"""

NAV_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en" xml:lang="en">
<head>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="styles/epub_style.css"/>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>{title}</h1>
    <ol>
{chapters}
    </ol>
  </nav>
</body>
</html>
"""

NCX_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{uid}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{title}</text></docTitle>
  <navMap>
{chapters}
  </navMap>
</ncx>
"""

CONTAINER_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a valid EPUB3 from chapter .md files")
    parser.add_argument("--title", default="Untitled Novel")
    parser.add_argument("--author", default="Unknown Author")
    parser.add_argument("--chapters", type=int, default=28)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    build_epub(args)
