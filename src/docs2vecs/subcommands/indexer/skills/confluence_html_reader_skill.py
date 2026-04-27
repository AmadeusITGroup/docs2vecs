"""Transformer skill: Confluence Scroll HTML Export → Markdown.

Converts ``.html`` files produced by the K15t Scroll HTML Exporter into clean,
self-contained Markdown.  Images referenced in the pages are copied into an
``images/`` sub-folder next to the Markdown files.

Typical pipeline position::

    scroll-html-exporter  →  confluence-html-to-markdown  →  file-scanner (*.md)

Config params
-------------
input_dir : str
    Path to the Scroll HTML export folder (the one containing the ``.html``
    files and the ``_scroll_external/`` asset directory).
output_dir : str, optional
    Destination for the ``.md`` files and ``images/`` folder.
    Defaults to ``<input_dir>/markdown``.
"""

import re
import shutil
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup, Tag
from markdownify import MarkdownConverter

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill

IMAGES_DIR_NAME = "images"


# ---------------------------------------------------------------------------
# Custom Markdown converter for Confluence / Scroll HTML
# ---------------------------------------------------------------------------
class _ConfluenceMarkdownConverter(MarkdownConverter):

    def convert_a(self, el, text, parent_tags=None, **kwargs):
        href = el.get("href", "")
        if "confluence-userlink" in el.get("class", []):
            return text.strip()
        if not href or href.startswith("#"):
            return text
        return super().convert_a(el, text, parent_tags=parent_tags, **kwargs)

    def convert_div(self, el, text, parent_tags=None, **kwargs):
        classes = el.get("class", [])
        layout_classes = {
            "contentLayout2", "columnLayout", "cell", "innerCell",
            "sectionColumnWrapper", "sectionMacro", "sectionMacroRow",
            "columnMacro", "panelContent",
        }
        if layout_classes & set(classes):
            return text
        if "panel" in classes:
            return text
        return text

    def convert_span(self, el, text, parent_tags=None, **kwargs):
        src = el.get("src", "")
        if src and "confluence-embedded-image" in el.get("class", []):
            alt = el.get("alt", "")
            return f"![{alt}]({src})"
        return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _extract_metadata(soup: BeautifulSoup) -> dict[str, str]:
    meta: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        name = tag.get("name", "")
        if name.startswith("exp-"):
            key = name.removeprefix("exp-")
            value = tag.get("content", "").strip()
            if value:
                meta[key] = value
    return meta


def _build_frontmatter(meta: dict[str, str]) -> str:
    lines = ["---"]
    field_map = {
        "page-title": "title",
        "page-created": "created",
        "page-last-modified": "modified",
        "page-labels": "labels",
        "space-title": "space",
        "document-title": "document",
    }
    for html_key, yaml_key in field_map.items():
        if html_key in meta:
            value = meta[html_key]
            if yaml_key == "title":
                value = f'"{value}"'
            lines.append(f"{yaml_key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _collect_and_rewrite_images(
    content_el: Tag,
    html_dir: Path,
    images_dir: Path,
) -> int:
    """Copy local images into *images_dir* and rewrite ``src`` attributes."""
    images_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    count = 0

    candidates: list[Tag] = []
    for img in content_el.find_all("img"):
        candidates.append(img)
    for span in content_el.find_all("span", class_="confluence-embedded-image"):
        if span.get("src"):
            candidates.append(span)

    for el in candidates:
        src = el.get("src", "")
        if not src or src.startswith(("http://", "https://", "data:")):
            continue
        if src in copied:
            el["src"] = copied[src]
            continue

        src_path = html_dir / src
        if not src_path.is_file():
            continue

        parts = Path(src).parts
        dest_name = f"{parts[-2]}-{parts[-1]}" if len(parts) >= 3 else parts[-1]
        dest_path = images_dir / dest_name
        if not dest_path.exists():
            shutil.copy2(src_path, dest_path)
            count += 1

        new_src = f"{IMAGES_DIR_NAME}/{dest_name}"
        el["src"] = new_src
        copied[src] = new_src

    return count


def _clean_html(content_el: Tag) -> None:
    for p in content_el.find_all("p"):
        if not p.get_text(strip=True) and not p.find("img"):
            p.decompose()
    for span in content_el.find_all("span", class_="confluence-anchor-link"):
        span.decompose()
    for span in content_el.find_all("span", class_="scroll-document-section-heading-counter"):
        span.decompose()
    for span in content_el.find_all("span", class_="scroll-document-section-heading-text"):
        span.unwrap()


def _convert_single_html(html_path: Path, images_dir: Path) -> tuple[str, str] | None:
    """Return *(clean_stem, markdown_text)* or *None* to skip."""
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    meta = _extract_metadata(soup)
    title = meta.get("page-title", "")

    main_el = soup.find("main", class_="exp-content")
    if not main_el:
        return None
    content_el = main_el.find("div", id="main-content")
    if not content_el:
        return None

    _collect_and_rewrite_images(content_el, html_path.parent, images_dir)
    _clean_html(content_el)

    converter = _ConfluenceMarkdownConverter(
        heading_style="atx",
        bullets="-",
        strip=["script", "style", "iframe", "nav"],
        newline_style="backslash",
    )
    md_body = converter.convert(str(content_el)).strip()
    md_body = re.sub(r"\n{3,}", "\n\n", md_body)
    md_body = "\n".join(line.rstrip() for line in md_body.splitlines())

    parts: list[str] = []
    if meta:
        parts.append(_build_frontmatter(meta))
    if title:
        parts.append(f"# {title}")
    parts.append(md_body)

    clean_stem = re.sub(r"\.\d+$", "", html_path.stem)
    return clean_stem, "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Skill
# ---------------------------------------------------------------------------
class ConfluenceHTMLToMarkdownSkill(IndexerSkill):
    """Transform a Scroll HTML export folder into self-contained Markdown."""

    def __init__(self, skill_config: dict, global_config: Config) -> None:
        super().__init__(skill_config, global_config)
        self._input_dir = Path(self._config["input_dir"]).expanduser().resolve()
        self._output_dir = (
            Path(self._config["output_dir"]).expanduser().resolve()
            if self._config.get("output_dir")
            else self._input_dir / "markdown"
        )

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        self.logger.info(
            "Running ConfluenceHTMLToMarkdownSkill  "
            f"input_dir={self._input_dir}  output_dir={self._output_dir}"
        )

        self._output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = self._output_dir / IMAGES_DIR_NAME

        skip_names = {"index", "search", "toc"}
        html_files = sorted(
            f for f in self._input_dir.glob("*.html")
            if f.stem.lower() not in skip_names
        )

        if not html_files:
            self.logger.warning(f"No HTML files found in {self._input_dir}")
            return input or []

        converted = 0
        for html_file in html_files:
            result = _convert_single_html(html_file, images_dir)
            if result is None:
                self.logger.debug(f"Skipped: {html_file.name}")
                continue

            stem, md_text = result
            out_path = self._output_dir / f"{stem}.md"
            out_path.write_text(md_text, encoding="utf-8")
            self.logger.info(f"Converted: {html_file.name} → {out_path.name}")
            converted += 1

        total_images = (
            sum(1 for _ in images_dir.iterdir() if _.is_file())
            if images_dir.exists()
            else 0
        )
        self.logger.info(
            f"Done. {converted}/{len(html_files)} pages converted, "
            f"{total_images} images copied → {self._output_dir}"
        )

        # Pass through whatever came in — downstream skills (e.g. file-scanner)
        # will pick up the markdown files from output_dir independently.
        return input or []
