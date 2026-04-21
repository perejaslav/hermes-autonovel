#!/usr/bin/env python3
"""
Build a valid EPUB3 from individual chapter .xhtml files.

Expected directory layout (created by this script):
  epub_build/          ← .md source files (one per chapter)
  epub_out/            ← pandoc .xhtml output (created here)
  EPUB/
    text/              ← final chapter .xhtml files
    styles/style.css
  the_speaking_tide.epub  ← final output

Usage:
  python build_epub.py [--chapters N] [--title TITLE] [--author AUTHOR]
"""

import argparse
import zipfile
import io
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
BUILD_DIR = ROOT / "epub_build"
OUT_DIR = ROOT / "epub_out"
EPUB_DIR = ROOT / "EPUB"
EPUB_TEXT_DIR = EPUB_DIR / "text"
EPUB_STYLES_DIR = EPUB_DIR / "styles"
EPUB_META_DIR = ROOT / "META-INF"


def natural_sort_key(s):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]


def collect_chapters(build_dir: Path) -> list[Path]:
    """Find all .md chapter files in epub_build/, sorted naturally."""
    chapters = sorted(build_dir.glob("ch_*.md"), key=lambda p: natural_sort_key(p.name))
    return chapters


def convert_markdown_to_xhtml(md_path: Path, out_path: Path):
    """Convert a single .md file to .xhtml using pandoc."""
    cmd = [
        "pandoc",
        str(md_path),
        "-o", str(out_path),
        "--from=markdown",
        "--to=html5",
        "--standalone",
        f"--css={EPUB_STYLES_DIR.name}/epub_style.css",
        "--metadata", "pagetitle=Chapter",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR converting {md_path.name}: {result.stderr}", file=sys.stderr)
        raise RuntimeError(result.stderr)
    print(f"  Converted {md_path.name} → {out_path.name}")


def build_epub(args):
    title = args.title
    author = args.author
    chapters_count = args.chapters
    epub_filename = args.output or f"{title.lower().replace(' ', '_')}.epub"

    print(f"Building EPUB: '{title}' by {author}")
    print(f"  Chapters: {chapters_count}")

    # ── 1. Create output directories ───────────────────────────────────────
    OUT_DIR.mkdir(exist_ok=True)
    EPUB_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    EPUB_STYLES_DIR.mkdir(parents=True, exist_ok=True)
    EPUB_META_DIR.mkdir(parents=True, exist_ok=True)

    # ── 2. Convert markdown → xhtml for each chapter ─────────────────────
    print("\n[1/5] Converting markdown → xhtml...")
    chapters = collect_chapters(BUILD_DIR)
    if not chapters:
        print(f"ERROR: No chapter files found in {BUILD_DIR}", file=sys.stderr)
        sys.exit(1)

    for md_path in chapters:
        xhtml_name = md_path.with_suffix(".xhtml").name
        xhtml_path = OUT_DIR / xhtml_name
        convert_markdown_to_xhtml(md_path, xhtml_path)

    # ── 3. Copy front/back matter ──────────────────────────────────────────
    print("\n[2/5] Copying front/back matter...")
    front = ROOT / "epub_front_matter.md"
    back = ROOT / "epub_back_cover.md"
    colophon = ROOT / "epub_colophon.md"

    if front.exists():
        convert_markdown_to_xhtml(front, OUT_DIR / "front_matter.xhtml")
    if back.exists():
        convert_markdown_to_xhtml(back, OUT_DIR / "back_cover.xhtml")
    if colophon.exists():
        convert_markdown_to_xhtml(colophon, OUT_DIR / "colophon.xhtml")

    # Copy style
    style_src = ROOT / "epub_style.css"
    if style_src.exists():
        import shutil
        shutil.copy(style_src, EPUB_STYLES_DIR / "epub_style.css")

    # ── 4. Build content.opf (manifest + spine) ────────────────────────────
    print("\n[3/5] Building content.opf...")

    all_xhtml = sorted(OUT_DIR.glob("*.xhtml"), key=lambda p: natural_sort_key(p.name))

    manifest_items = []
    spine_items = []

    # Front matter
    fm = OUT_DIR / "front_matter.xhtml"
    if fm.exists():
        manifest_items.append(f'    <item id="front_matter" href="text/front_matter.xhtml" media-type="application/xhtml+xml"/>')
        spine_items.append('      <itemref idref="front_matter"/>')

    # Chapters
    for i, xhtml_path in enumerate(all_xhtml, 1):
        if xhtml_path.name in ("front_matter.xhtml", "back_cover.xhtml", "colophon.xhtml"):
            continue
        chapter_id = xhtml_path.stem  # e.g. "ch_01"
        manifest_items.append(f'    <item id="{chapter_id}" href="text/{xhtml_path.name}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'      <itemref idref="{chapter_id}"/>')

    # Back cover
    bc = OUT_DIR / "back_cover.xhtml"
    if bc.exists():
        manifest_items.append('    <item id="back_cover" href="text/back_cover.xhtml" media-type="application/xhtml+xml"/>')
        spine_items.append('      <itemref idref="back_cover"/>')

    # Colophon
    col = OUT_DIR / "colophon.xhtml"
    if col.exists():
        manifest_items.append('    <item id="colophon" href="text/colophon.xhtml" media-type="application/xhtml+xml"/>')
        spine_items.append('      <itemref idref="colophon"/>')

    manifest_items.append('    <item id="css" href="styles/epub_style.css" media-type="text/css"/>')
    manifest_items.append('    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
    manifest_items.append('    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')

    spine = "\n".join(spine_items)
    manifest = "\n".join(manifest_items)

    opf_content = OPF_TEMPLATE.format(
        title=title,
        author=author,
        manifest=manifest,
        spine=spine,
    )
    opf_path = EPUB_DIR / "content.opf"
    opf_path.write_text(opf_content, encoding="utf-8")
    print(f"  Written {opf_path}")

    # ── 5. Build nav.xhtml (EPUB3 navigation) ──────────────────────────────
    print("\n[4/5] Building nav.xhtml...")

    nav_chapters = []
    for i, xhtml_path in enumerate(all_xhtml, 1):
        if xhtml_path.name in ("front_matter.xhtml", "back_cover.xhtml", "colophon.xhtml"):
            continue
        chapter_id = xhtml_path.stem
        # Extract chapter title from xhtml
        content = xhtml_path.read_text(encoding="utf-8")
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
        ch_title = title_match.group(1).strip() if title_match else f"Chapter {i}"
        nav_chapters.append(f'      <li><a href="text/{xhtml_path.name}">{ch_title}</a></li>')

    nav_content = NAV_TEMPLATE.format(
        title=title,
        chapters="\n".join(nav_chapters),
    )
    nav_path = EPUB_DIR / "nav.xhtml"
    nav_path.write_text(nav_content, encoding="utf-8")
    print(f"  Written {nav_path}")

    # ── 6. Build toc.ncx (legacy navigation) ───────────────────────────────
    ncx_content = NCX_TEMPLATE.format(
        title=title,
        uid="nov-001",
        chapters="\n".join([
            f'      <navPoint id="navpoint-{i}" playOrder="{i}">\n        <navLabel><text>{p.stem.replace("ch_", "Chapter ")}</text></navLabel>\n        <content src="text/{p.name}"/>\n      </navPoint>'
            for i, p in enumerate([x for x in all_xhtml if x.name not in ("front_matter.xhtml", "back_cover.xhtml", "colophon.xhtml")], 1)
        ]),
    )
    ncx_path = EPUB_DIR / "toc.ncx"
    ncx_path.write_text(ncx_content, encoding="utf-8")
    print(f"  Written {ncx_path}")

    # ── 7. Copy chapter xhtml files to EPUB/text/ ─────────────────────────
    print("\n[5/5] Assembling EPUB archive...")
    for xhtml_path in OUT_DIR.glob("*.xhtml"):
        dest = EPUB_TEXT_DIR / xhtml_path.name
        dest.write_text(xhtml_path.read_text(encoding="utf-8"), encoding="utf-8")

    # ── 8. Write container.xml ─────────────────────────────────────────────
    container_content = CONTAINER_TEMPLATE
    EPUB_META_DIR.joinpath("container.xml").write_text(container_content, encoding="utf-8")

    # ── 9. Create mimetype (UNCOMPRESSED first) ────────────────────────────
    mimetype_path = ROOT / "mimetype"
    mimetype_path.write_text("application/epub+zip", encoding="utf-8")

    # ── 10. Zip it all together (mimetype first, uncompressed) ────────────
    epub_path = ROOT / epub_filename
    with zipfile.ZipFile(str(epub_path), "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype MUST be first and uncompressed
        zf.write(str(mimetype_path), arcname="mimetype", compress_type=zipfile.ZIP_STORED)

        # META-INF/
        meta_files = list(EPUB_META_DIR.glob("*"))
        for f in meta_files:
            zf.write(str(f), arcname=f"META-INF/{f.name}")

        # EPUB/
        for f in EPUB_DIR.rglob("*"):
            if f.is_file():
                arcname = str(f.relative_to(ROOT))
                zf.write(str(f), arcname=arcname)

    size_kb = epub_path.stat().st_size // 1024
    print(f"\n✅ EPUB created: {epub_path} ({size_kb} KB)")

    # Cleanup mimetype from ROOT
    mimetype_path.unlink()


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
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
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
    parser = argparse.ArgumentParser(description="Build a valid EPUB3 from chapter files")
    parser.add_argument("--title", default="Untitled Novel", help="Book title")
    parser.add_argument("--author", default="Unknown Author", help="Author name")
    parser.add_argument("--chapters", type=int, default=28, help="Expected number of chapters")
    parser.add_argument("--output", default=None, help="Output EPUB filename")
    args = parser.parse_args()

    build_epub(args)
