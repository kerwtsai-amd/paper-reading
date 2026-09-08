#!/usr/bin/env python3
"""Build the public Paper Reading site without publishing local PDFs.

The source tree remains the research workspace.  This builder only accepts paper
summaries at ``<Topic>/<Subtopic>/<Paper>/summary.html`` and emits a separate,
deterministic ``_site`` tree suitable for GitHub Pages.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import os
import re
import shutil
import stat
import time
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY_NAME = "_site"
NORMALIZED_MTIME = 946_684_800  # 2000-01-01T00:00:00Z

ARXIV_PATH_RE = re.compile(
    r"^/(?:abs|pdf)/(?P<id>(?:\d{4}\.\d{4,5}|[a-z][a-z.\-]+/\d{7})(?:v\d+)?)(?:\.pdf)?/?$",
    re.IGNORECASE,
)
ARXIV_VERSION_RE = re.compile(r"v(?P<version>\d+)$", re.IGNORECASE)
ANCHOR_TAG_RE = re.compile(r"<a\b[^>]*>", re.IGNORECASE)
HREF_RE = re.compile(
    r"(?P<prefix>\bhref\s*=\s*)(?P<quote>['\"])(?P<url>.*?)(?P=quote)",
    re.IGNORECASE,
)
DOWNLOAD_ATTR_RE = re.compile(
    r"\s+download(?:\s*=\s*(?:['\"][^'\"]*['\"]|[^\s>]+))?",
    re.IGNORECASE,
)
TARGET_ATTR_RE = re.compile(r"\s+target\s*=", re.IGNORECASE)
REL_ATTR_RE = re.compile(r"\s+rel\s*=", re.IGNORECASE)
HEAD_OPEN_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
ROBOTS_META_RE = re.compile(
    r"<meta\b(?=[^>]*\bname\s*=\s*['\"]robots['\"])[^>]*>",
    re.IGNORECASE,
)
PUBLISHABLE_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})


class BuildError(RuntimeError):
    """Raised when a source summary cannot be published safely."""


@dataclass(frozen=True)
class Anchor:
    href: str
    text: str


@dataclass(frozen=True)
class Source:
    kind: str
    key: str
    url: str


@dataclass(frozen=True)
class SourceCandidate:
    score: int
    anchor_index: int
    source: Source


@dataclass(frozen=True)
class Paper:
    topic: str
    subtopic: str
    directory_name: str
    title: str
    summary_path: Path
    relative_directory: Path
    source: Source | None
    slug: str
    image_paths: tuple[PurePosixPath, ...]


class SummaryMetadataParser(HTMLParser):
    """Collect just enough metadata without rewriting the source document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1_parts: list[str] = []
        self.title_parts: list[str] = []
        self.anchors: list[Anchor] = []
        self.image_sources: list[str] = []
        self._h1_depth = 0
        self._title_depth = 0
        self._anchor_href: str | None = None
        self._anchor_parts: list[str] = []
        self._suppressed_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.casefold()
        if tag in {"script", "style"}:
            self._suppressed_depth += 1
        if tag == "h1":
            self._h1_depth += 1
        elif tag == "title":
            self._title_depth += 1
        elif tag == "a":
            attr_map = {name.casefold(): value or "" for name, value in attrs}
            self._anchor_href = attr_map.get("href")
            self._anchor_parts = []
        elif tag == "img":
            attr_map = {name.casefold(): value or "" for name, value in attrs}
            if "src" in attr_map:
                self.image_sources.append(attr_map["src"])

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag == "h1" and self._h1_depth:
            self._h1_depth -= 1
        elif tag == "title" and self._title_depth:
            self._title_depth -= 1
        elif tag == "a" and self._anchor_href is not None:
            self.anchors.append(
                Anchor(self._anchor_href, _collapse_whitespace(self._anchor_parts))
            )
            self._anchor_href = None
            self._anchor_parts = []
        if tag in {"script", "style"} and self._suppressed_depth:
            self._suppressed_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._suppressed_depth:
            return
        if self._h1_depth:
            self.h1_parts.append(data)
        if self._title_depth:
            self.title_parts.append(data)
        if self._anchor_href is not None:
            self._anchor_parts.append(data)


def _collapse_whitespace(parts: list[str]) -> str:
    return " ".join("".join(parts).split())


def _normalized_sort_key(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _read_summary(path: Path) -> tuple[str, SummaryMetadataParser]:
    try:
        document = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise BuildError(f"Summary is not valid UTF-8: {path}") from exc

    parser = SummaryMetadataParser()
    parser.feed(document)
    parser.close()
    return document, parser


def _arxiv_match(value: str) -> tuple[str, str] | None:
    match = ARXIV_PATH_RE.fullmatch(unquote(value))
    if not match:
        return None
    versioned_id = match.group("id")
    base_id = ARXIV_VERSION_RE.sub("", versioned_id)
    return base_id, versioned_id


def _source_from_metadata(parser: SummaryMetadataParser) -> Source | None:
    candidates: list[SourceCandidate] = []
    for anchor_index, anchor in enumerate(parser.anchors):
        parsed = urlsplit(html.unescape(anchor.href))
        host = (parsed.hostname or "").casefold()
        if parsed.scheme not in {"http", "https"} or not host:
            continue
        label = _normalized_sort_key(anchor.text)
        authority_score = _source_anchor_authority_score(label)

        if host == "arxiv.org" or host.endswith(".arxiv.org"):
            arxiv = _arxiv_match(parsed.path)
            if not arxiv:
                continue
            base_id, versioned_id = arxiv
            score = 10 + authority_score
            if "arxiv:" in label or label.startswith("arxiv"):
                score += 40
            candidates.append(
                SourceCandidate(
                    score=score,
                    anchor_index=anchor_index,
                    source=Source(
                        kind="arxiv",
                        key=base_id.casefold(),
                        url=f"https://arxiv.org/pdf/{versioned_id}",
                    ),
                )
            )
            continue

        if host in {"doi.org", "dx.doi.org"}:
            doi = unquote(parsed.path).lstrip("/").strip()
            if not doi:
                continue
            score = 10 + authority_score
            if label.startswith("doi") or " doi" in label:
                score += 40
            candidates.append(
                SourceCandidate(
                    score=score,
                    anchor_index=anchor_index,
                    source=Source(
                        kind="doi",
                        key=doi.casefold(),
                        url=f"https://doi.org/{doi}",
                    ),
                )
            )
            continue

        # A generic external URL is only eligible when its own anchor clearly
        # identifies it as the paper/project landing page.
        if authority_score:
            normalized_url = parsed._replace(fragment="").geturl()
            candidates.append(
                SourceCandidate(
                    score=10 + authority_score,
                    anchor_index=anchor_index,
                    source=Source(
                        kind="landing",
                        key=normalized_url.casefold(),
                        url=normalized_url,
                    ),
                )
            )

    if not candidates:
        return None

    # Each anchor stands on its own: repeated unrelated citations never gain
    # authority by accumulation.  Collapse multiple anchors for one normalized
    # identity before comparing sources (arXiv versions share the base ID).
    best_by_identity: dict[tuple[str, str], SourceCandidate] = {}
    for candidate in candidates:
        identity = (candidate.source.kind, candidate.source.key)
        previous = best_by_identity.get(identity)
        if previous is None or (
            -candidate.score,
            candidate.anchor_index,
            candidate.source.url.casefold(),
        ) < (
            -previous.score,
            previous.anchor_index,
            previous.source.url.casefold(),
        ):
            best_by_identity[identity] = candidate

    # Earliest source order and normalized URL provide a deterministic tie-break
    # without preferring one source type.
    return sorted(
        best_by_identity.values(),
        key=lambda candidate: (
            -candidate.score,
            candidate.anchor_index,
            candidate.source.url.casefold(),
        ),
    )[0].source


def _source_anchor_authority_score(label: str) -> int:
    if "canonical" in label:
        return 300
    paper_page_labels = (
        "論文頁面",
        "paper page",
        "project page",
        "publisher page",
        "official paper",
    )
    if any(marker in label for marker in paper_page_labels):
        return 200
    return 0


def _slug_for(source: Source | None, relative_directory: Path) -> str:
    if source and source.kind == "arxiv":
        safe_id = re.sub(r"[^a-z0-9]+", "-", source.key).strip("-")
        return f"arxiv-{safe_id}"
    if source and source.kind == "doi":
        digest = hashlib.sha256(source.key.encode("utf-8")).hexdigest()[:10]
        return f"doi-{digest}"

    identity = source.key if source else relative_directory.as_posix()
    normalized_identity = unicodedata.normalize("NFKC", identity).casefold()
    digest = hashlib.sha256(normalized_identity.encode("utf-8")).hexdigest()[:10]
    return f"paper-{digest}"


def discover_papers(root: Path) -> list[Paper]:
    root = root.resolve()
    papers: list[Paper] = []

    for summary_path in sorted(
        root.rglob("summary.html"),
        key=lambda path: _normalized_sort_key(path.relative_to(root).as_posix()),
    ):
        relative_path = summary_path.relative_to(root)
        if len(relative_path.parts) != 4:
            continue
        if any(part.startswith(".") for part in relative_path.parts):
            continue
        if summary_path.is_symlink():
            raise BuildError(f"Refusing to publish a symlinked summary: {relative_path}")

        document, parser = _read_summary(summary_path)
        del document
        title = _collapse_whitespace(parser.h1_parts)
        if not title:
            title = _collapse_whitespace(parser.title_parts)
            title = re.sub(r"\s*[｜|]\s*Paper Reading\s*$", "", title).strip()
        if not title:
            raise BuildError(f"Summary has no usable h1/title: {relative_path}")

        topic, subtopic, directory_name, _ = relative_path.parts
        relative_directory = relative_path.parent
        source = _source_from_metadata(parser)
        if source is None:
            raise BuildError(
                "No canonical arXiv, DOI, or paper landing page was found: "
                f"{relative_path}"
            )
        image_paths = _validate_image_references(summary_path, parser)
        papers.append(
            Paper(
                topic=topic,
                subtopic=subtopic,
                directory_name=directory_name,
                title=title,
                summary_path=summary_path,
                relative_directory=relative_directory,
                source=source,
                slug=_slug_for(source, relative_directory),
                image_paths=image_paths,
            )
        )

    if not papers:
        raise BuildError(
            "No summaries found at <Topic>/<Subtopic>/<Paper>/summary.html."
        )

    papers.sort(
        key=lambda paper: (
            _normalized_sort_key(paper.topic),
            _normalized_sort_key(paper.subtopic),
            _normalized_sort_key(paper.title),
            paper.relative_directory.as_posix(),
        )
    )

    seen_slugs: dict[str, Paper] = {}
    for paper in papers:
        previous = seen_slugs.get(paper.slug)
        if previous:
            raise BuildError(
                "Two summaries resolve to the same stable URL "
                f"'{paper.slug}': {previous.relative_directory} and "
                f"{paper.relative_directory}"
            )
        seen_slugs[paper.slug] = paper

    return papers


def _is_relative_pdf_href(value: str) -> bool:
    decoded = html.unescape(value).strip()
    parsed = urlsplit(decoded)
    if parsed.scheme or parsed.netloc or decoded.startswith(("/", "#", "//")):
        return False
    return unquote(parsed.path).casefold().endswith(".pdf")


def _rewrite_summary(document: str, paper: Paper) -> str:
    saw_relative_pdf = False

    def replace_anchor(match: re.Match[str]) -> str:
        nonlocal saw_relative_pdf
        tag = match.group(0)
        href_match = HREF_RE.search(tag)
        if not href_match or not _is_relative_pdf_href(href_match.group("url")):
            return tag
        saw_relative_pdf = True
        if paper.source is None:
            return tag

        escaped_url = html.escape(paper.source.url, quote=True)
        rewritten = HREF_RE.sub(
            lambda href: (
                href.group("prefix")
                + href.group("quote")
                + escaped_url
                + href.group("quote")
            ),
            tag,
            count=1,
        )
        rewritten = DOWNLOAD_ATTR_RE.sub("", rewritten)
        closing = "/>" if rewritten.endswith("/>") else ">"
        body = rewritten[: -len(closing)]
        if not TARGET_ATTR_RE.search(rewritten):
            body += ' target="_blank"'
        if not REL_ATTR_RE.search(rewritten):
            body += ' rel="noopener noreferrer"'
        return body + closing

    rewritten = ANCHOR_TAG_RE.sub(replace_anchor, document)
    if saw_relative_pdf and paper.source is None:
        raise BuildError(
            "Cannot replace a local PDF link because no canonical arXiv, DOI, or "
            f"paper landing page was found: {paper.relative_directory}"
        )

    replacements = (
        ("↓ 開啟本地 PDF", "↗ 原始來源"),
        ("開啟本地 PDF", "開啟原始來源"),
        ("本地 PDF", "原始來源"),
    )
    for old, new in replacements:
        rewritten = rewritten.replace(old, new)
    return _inject_robots_policy(rewritten, paper.relative_directory)


def _inject_robots_policy(document: str, relative_directory: Path) -> str:
    robots_meta = '<meta name="robots" content="noindex, noarchive">'
    if ROBOTS_META_RE.search(document):
        return ROBOTS_META_RE.sub(robots_meta, document, count=1)
    head_match = HEAD_OPEN_RE.search(document)
    if not head_match:
        raise BuildError(f"Summary has no head element: {relative_directory}")
    return (
        document[: head_match.end()]
        + "\n  "
        + robots_meta
        + document[head_match.end() :]
    )


def _validate_image_references(
    summary_path: Path, parser: SummaryMetadataParser
) -> tuple[PurePosixPath, ...]:
    images_directory = summary_path.parent / "assets" / "images"
    if images_directory.is_symlink() or not images_directory.is_dir():
        raise BuildError(
            f"Missing real assets/images directory: {summary_path.relative_to(summary_path.parents[3])}"
        )
    resolved_images_directory = images_directory.resolve()
    referenced_images: set[PurePosixPath] = set()

    candidates = [(raw_source, True) for raw_source in parser.image_sources]
    candidates.extend((anchor.href, False) for anchor in parser.anchors)
    for raw_source, required_image in candidates:
        source = html.unescape(raw_source).strip()
        parsed = urlsplit(source)
        if parsed.scheme or parsed.netloc or source.startswith("//"):
            continue
        if not parsed.path:
            if required_image:
                raise BuildError(
                    f"Image src has no path in {summary_path}: {raw_source!r}"
                )
            continue
        decoded_path = unquote(parsed.path)
        if "\\" in decoded_path:
            if required_image or decoded_path.casefold().startswith("assets\\images\\"):
                raise BuildError(
                    f"Image reference must use forward slashes in {summary_path}: {raw_source}"
                )
            continue
        relative_image = PurePosixPath(decoded_path)
        if relative_image.is_absolute() or ".." in relative_image.parts:
            if required_image:
                raise BuildError(
                    f"Image src escapes the paper directory in {summary_path}: {raw_source}"
                )
            continue
        under_images = (
            len(relative_image.parts) >= 3
            and relative_image.parts[:2] == ("assets", "images")
        )
        if not under_images:
            if not required_image:
                continue
            raise BuildError(
                "Relative image src must be under assets/images in "
                f"{summary_path}: {raw_source}"
            )
        if relative_image.suffix.casefold() not in PUBLISHABLE_IMAGE_SUFFIXES:
            raise BuildError(
                f"Image type is not publishable in {summary_path}: {raw_source}"
            )

        source_path = summary_path.parent.joinpath(*relative_image.parts)
        cursor = summary_path.parent
        for part in relative_image.parts:
            cursor /= part
            if cursor.is_symlink():
                raise BuildError(f"Refusing a symlinked image path: {source_path}")
        if not source_path.is_file():
            raise BuildError(
                f"Referenced image does not exist as a regular file: {source_path}"
            )
        try:
            source_path.resolve().relative_to(resolved_images_directory)
        except ValueError as exc:
            raise BuildError(
                f"Referenced image resolves outside assets/images: {source_path}"
            ) from exc
        _validate_raster_signature(source_path)
        referenced_images.add(relative_image)

    return tuple(sorted(referenced_images, key=lambda path: path.as_posix().casefold()))


def _validate_raster_signature(path: Path) -> None:
    with path.open("rb") as image_file:
        header = image_file.read(16)
    suffix = path.suffix.casefold()
    valid = {
        ".png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": header.startswith(b"\xff\xd8\xff"),
        ".jpeg": header.startswith(b"\xff\xd8\xff"),
        ".gif": header.startswith((b"GIF87a", b"GIF89a")),
        ".webp": len(header) >= 12
        and header.startswith(b"RIFF")
        and header[8:12] == b"WEBP",
    }.get(suffix, False)
    if not valid:
        raise BuildError(f"Referenced image has an invalid {suffix} signature: {path}")


def _copy_assets(
    source_directory: Path,
    destination_directory: Path,
    image_paths: tuple[PurePosixPath, ...],
) -> None:
    assets_directory = source_directory / "assets" / "images"
    if assets_directory.is_symlink() or not assets_directory.is_dir():
        raise BuildError(f"assets/images must be a real directory: {assets_directory}")

    for image_path in image_paths:
        relative_path = Path(*image_path.parts[2:])
        source_path = assets_directory / relative_path
        if source_path.is_symlink() or not source_path.is_file():
            raise BuildError(f"Referenced image changed during build: {source_path}")
        _validate_raster_signature(source_path)
        destination_path = destination_directory / "assets" / "images" / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, destination_path)


def _render_index(papers: list[Paper]) -> str:
    grouped: dict[str, dict[str, list[Paper]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for paper in papers:
        grouped[paper.topic][paper.subtopic].append(paper)

    topic_sections: list[str] = []
    for topic in sorted(grouped, key=_normalized_sort_key):
        subtopic_sections: list[str] = []
        for subtopic in sorted(grouped[topic], key=_normalized_sort_key):
            cards: list[str] = []
            for paper in grouped[topic][subtopic]:
                search_text = " ".join(
                    (paper.topic, paper.subtopic, paper.title, paper.directory_name)
                )
                source_link = ""
                if paper.source:
                    source_link = (
                        '<a class="source-link" href="'
                        + html.escape(paper.source.url, quote=True)
                        + '" target="_blank" rel="noopener noreferrer">原始來源 ↗</a>'
                    )
                cards.append(
                    '<article class="paper-card" data-paper '
                    f'data-search="{html.escape(search_text, quote=True)}">'
                    f'<h3><a href="papers/{paper.slug}/">'
                    f"{html.escape(paper.title)}</a></h3>"
                    '<div class="paper-meta">'
                    f"<span>{html.escape(paper.topic)}</span>"
                    '<span aria-hidden="true">›</span>'
                    f"<span>{html.escape(paper.subtopic)}</span>"
                    "</div>"
                    f'<div class="paper-actions"><a href="papers/{paper.slug}/">'
                    f"閱讀摘要</a>{source_link}</div>"
                    "</article>"
                )
            subtopic_sections.append(
                '<section class="subtopic" data-subtopic-group>'
                f"<h2>{html.escape(subtopic)}</h2>"
                '<div class="paper-grid">'
                + "".join(cards)
                + "</div></section>"
            )
        topic_sections.append(
            '<section class="topic" data-topic-group>'
            f"<h2>{html.escape(topic)}</h2>"
            + "".join(subtopic_sections)
            + "</section>"
        )

    return """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, noarchive">
  <meta name="description" content="繁體中文論文深度閱讀摘要索引">
  <title>Paper Reading｜論文閱讀</title>
  <style>
    :root { color-scheme: light dark; --bg: #f5f7fb; --panel: #fff; --text: #172033; --muted: #647089; --line: #dce2ec; --accent: #3157d5; --accent-soft: #e9edff; }
    @media (prefers-color-scheme: dark) { :root { --bg: #10131b; --panel: #181d29; --text: #eef2ff; --muted: #aab3c7; --line: #30394c; --accent: #9db1ff; --accent-soft: #252e50; } }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, "Segoe UI", sans-serif; line-height: 1.6; }
    a { color: var(--accent); }
    .shell { width: min(1120px, calc(100% - 2rem)); margin: 0 auto; }
    header { padding: 4rem 0 2rem; }
    .eyebrow { margin: 0 0 .4rem; color: var(--accent); font-size: .78rem; font-weight: 750; letter-spacing: .12em; text-transform: uppercase; }
    h1 { margin: 0; font-size: clamp(2rem, 5vw, 3.5rem); line-height: 1.12; }
    .intro { max-width: 46rem; margin: .8rem 0 1.5rem; color: var(--muted); }
    .search-box { position: relative; max-width: 42rem; }
    .search-box label { display: block; margin-bottom: .45rem; font-weight: 700; }
    .search-box input { width: 100%; border: 1px solid var(--line); border-radius: .8rem; background: var(--panel); color: var(--text); padding: .85rem 1rem; font: inherit; }
    .search-box input:focus { outline: 3px solid var(--accent-soft); border-color: var(--accent); }
    #result-status { margin: .55rem 0 0; color: var(--muted); font-size: .92rem; }
    main { padding-bottom: 4rem; }
    .topic { margin-top: 2.5rem; }
    .topic > h2 { margin: 0 0 1rem; font-size: 1.6rem; }
    .subtopic { margin: 1.4rem 0 2rem; }
    .subtopic > h2 { margin: 0 0 .75rem; color: var(--muted); font-size: 1.05rem; }
    .paper-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 1rem; }
    .paper-card { display: flex; min-height: 11rem; flex-direction: column; border: 1px solid var(--line); border-radius: 1rem; background: var(--panel); padding: 1.1rem; box-shadow: 0 8px 24px rgb(16 24 40 / .05); }
    .paper-card h3 { margin: 0; font-size: 1.05rem; line-height: 1.45; }
    .paper-card h3 a { color: var(--text); text-decoration: none; }
    .paper-card h3 a:hover { color: var(--accent); text-decoration: underline; }
    .paper-meta { display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .8rem; color: var(--muted); font-size: .84rem; }
    .paper-actions { display: flex; flex-wrap: wrap; gap: .9rem; margin-top: auto; padding-top: 1rem; font-weight: 700; font-size: .9rem; }
    .source-link { color: var(--muted); font-weight: 600; }
    [hidden] { display: none !important; }
  </style>
</head>
<body>
  <header class="shell">
    <p class="eyebrow">Paper Reading</p>
    <h1>論文閱讀</h1>
    <p class="intro">依技術主題整理的繁體中文深度閱讀摘要。搜尋會同時比對主題、子題與論文標題。</p>
    <div class="search-box">
      <label for="paper-search">搜尋論文</label>
      <input id="paper-search" type="search" placeholder="例如：KV cache、serving、Prefill" autocomplete="off">
      <p id="result-status" role="status" aria-live="polite">共 PAPER_COUNT 篇</p>
    </div>
  </header>
  <main class="shell" id="paper-list">
    TOPIC_SECTIONS
    <p id="empty-state" hidden>找不到符合條件的論文。</p>
  </main>
  <script>
    (() => {
      const input = document.querySelector("#paper-search");
      const papers = [...document.querySelectorAll("[data-paper]")];
      const status = document.querySelector("#result-status");
      const empty = document.querySelector("#empty-state");
      const normalize = (value) => value.normalize("NFKC").toLocaleLowerCase("zh-Hant");
      const update = () => {
        const terms = normalize(input.value).trim().split(/\\s+/).filter(Boolean);
        let visible = 0;
        for (const paper of papers) {
          const haystack = normalize(paper.dataset.search || "");
          const matches = terms.every((term) => haystack.includes(term));
          paper.hidden = !matches;
          if (matches) visible += 1;
        }
        for (const group of document.querySelectorAll("[data-subtopic-group]")) {
          group.hidden = !group.querySelector("[data-paper]:not([hidden])");
        }
        for (const group of document.querySelectorAll("[data-topic-group]")) {
          group.hidden = !group.querySelector("[data-paper]:not([hidden])");
        }
        status.textContent = terms.length ? `顯示 ${visible} / ${papers.length} 篇` : `共 ${papers.length} 篇`;
        empty.hidden = visible !== 0;
      };
      input.addEventListener("input", update);
    })();
  </script>
</body>
</html>
""".replace("PAPER_COUNT", str(len(papers))).replace(
        "TOPIC_SECTIONS", "".join(topic_sections)
    )


def _safe_remove_build_directory(path: Path, root: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.name not in {OUTPUT_DIRECTORY_NAME, f"{OUTPUT_DIRECTORY_NAME}.__building__"}:
        raise BuildError(f"Refusing to replace unexpected build path: {path}")
    if path.is_symlink():
        raise BuildError(f"Refusing to replace a symlinked build path: {path}")
    try:
        path.parent.resolve().relative_to(root.resolve())
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise BuildError(f"Refusing to replace a build path outside root: {path}") from exc
    if not path.is_dir():
        raise BuildError(f"Build path exists but is not a directory: {path}")
    def clear_readonly_and_retry(function: object, target: str, _: object) -> None:
        os.chmod(target, stat.S_IWRITE)
        function(target)  # type: ignore[operator]

    for attempt in range(4):
        try:
            shutil.rmtree(path, onerror=clear_readonly_and_retry)
            return
        except PermissionError:
            if attempt == 3:
                raise
            time.sleep(0.1 * (2**attempt))


def _normalize_timestamps(directory: Path) -> None:
    paths = sorted(
        directory.rglob("*"),
        key=lambda path: (len(path.parts), path.as_posix()),
        reverse=True,
    )
    for path in paths:
        # Symlinks have already been rejected by _assert_publication_boundary.
        # Avoid follow_symlinks=False because Windows does not implement that
        # combination for os.utime.
        os.utime(path, (NORMALIZED_MTIME, NORMALIZED_MTIME))
    os.utime(directory, (NORMALIZED_MTIME, NORMALIZED_MTIME))


def _assert_publication_boundary(site_directory: Path) -> None:
    for output_path in site_directory.rglob("*"):
        relative_path = output_path.relative_to(site_directory)
        if output_path.is_symlink():
            raise BuildError(f"Generated site contains a symlink: {relative_path}")
        if output_path.is_file() and output_path.suffix.casefold() == ".pdf":
            raise BuildError(f"Generated site contains a PDF: {relative_path}")
        if any(part.casefold() == ".agents" for part in relative_path.parts):
            raise BuildError(f"Generated site contains .agents content: {relative_path}")
        if output_path.name.casefold() == "agents.md":
            raise BuildError(f"Generated site contains AGENTS.md: {relative_path}")


def _build_site(
    root: Path, output_directory: Path, *, allow_nested_output: bool
) -> list[Paper]:
    root = root.resolve()
    output_directory = Path(os.path.abspath(os.fspath(output_directory)))
    if output_directory.name != OUTPUT_DIRECTORY_NAME:
        raise BuildError(
            f"The output directory must be named '{OUTPUT_DIRECTORY_NAME}': "
            f"{output_directory}"
        )
    if output_directory.is_symlink():
        raise BuildError(f"Refusing a symlinked output directory: {output_directory}")
    if not allow_nested_output and output_directory != root / OUTPUT_DIRECTORY_NAME:
        raise BuildError(f"Output must be exactly {root / OUTPUT_DIRECTORY_NAME}")
    try:
        output_directory.parent.resolve().relative_to(root)
    except ValueError as exc:
        raise BuildError(f"Output must remain inside project root: {output_directory}") from exc

    papers = discover_papers(root)
    staging_directory = output_directory.with_name(
        f"{OUTPUT_DIRECTORY_NAME}.__building__"
    )
    _safe_remove_build_directory(staging_directory, root)
    staging_directory.mkdir(parents=True)

    try:
        for paper in papers:
            document = paper.summary_path.read_text(encoding="utf-8")
            rewritten = _rewrite_summary(document, paper)
            paper_output = staging_directory / "papers" / paper.slug
            paper_output.mkdir(parents=True)
            (paper_output / "index.html").write_text(
                rewritten, encoding="utf-8", newline="\n"
            )
            _copy_assets(paper.summary_path.parent, paper_output, paper.image_paths)

        (staging_directory / "index.html").write_text(
            _render_index(papers), encoding="utf-8", newline="\n"
        )
        (staging_directory / ".nojekyll").write_text(
            "", encoding="utf-8", newline="\n"
        )
        _assert_publication_boundary(staging_directory)
        _normalize_timestamps(staging_directory)

        _safe_remove_build_directory(output_directory, root)
        # Copy the completed staging tree into place instead of renaming the
        # directory.  OneDrive can transiently deny directory renames on
        # Windows even when every file handle is closed.
        try:
            shutil.copytree(
                staging_directory,
                output_directory,
                copy_function=shutil.copyfile,
            )
            _normalize_timestamps(output_directory)
        except Exception:
            _safe_remove_build_directory(output_directory, root)
            raise
        _safe_remove_build_directory(staging_directory, root)
    except Exception:
        _safe_remove_build_directory(staging_directory, root)
        raise

    return papers


def build_site(root: Path, output_directory: Path) -> list[Paper]:
    """Build to the one permitted public output, ``<root>/_site``."""
    return _build_site(root, output_directory, allow_nested_output=False)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="build and validate in a temporary directory without changing _site",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.check:
            check_parent = PROJECT_ROOT / f"_site.__check__-{os.getpid()}"
            if check_parent.exists() or check_parent.is_symlink():
                raise BuildError(f"Temporary check path already exists: {check_parent}")
            check_parent.mkdir()
            try:
                papers = _build_site(
                    PROJECT_ROOT,
                    check_parent / OUTPUT_DIRECTORY_NAME,
                    allow_nested_output=True,
                )
            finally:
                if check_parent.exists() and not check_parent.is_symlink():
                    shutil.rmtree(check_parent)
            print(f"Site check passed for {len(papers)} paper(s); _site was not changed.")
        else:
            output_directory = PROJECT_ROOT / OUTPUT_DIRECTORY_NAME
            papers = build_site(PROJECT_ROOT, output_directory)
            print(f"Built {len(papers)} paper(s) in {output_directory}")
    except (BuildError, OSError) as exc:
        print(f"Site build failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
