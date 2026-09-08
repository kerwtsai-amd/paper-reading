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
from datetime import date
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit


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
PARAGRAPH_ELEMENT_RE = re.compile(
    r"<p\b(?P<attributes>[^>]*)>.*?</p\s*>", re.IGNORECASE | re.DOTALL
)
CLASS_ATTRIBUTE_RE = re.compile(
    r"(?:^|\s)class\s*=\s*(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
INVALID_PERCENT_ESCAPE_RE = re.compile(r"%(?![0-9a-fA-F]{2})")
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
    last_updated: date


class SummaryMetadataParser(HTMLParser):
    """Collect just enough metadata without rewriting the source document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1_parts: list[str] = []
        self.title_parts: list[str] = []
        self.anchors: list[Anchor] = []
        self.image_sources: list[str] = []
        self.summary_update_datetimes: list[list[str]] = []
        self._h1_depth = 0
        self._title_depth = 0
        self._anchor_href: str | None = None
        self._anchor_parts: list[str] = []
        self._dt_depth = 0
        self._dt_parts: list[str] = []
        self._pending_summary_update_index: int | None = None
        self._summary_update_dd_index: int | None = None
        self._suppressed_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.casefold()
        if tag in {"script", "style"}:
            self._suppressed_depth += 1

        # A summary date is metadata only when it belongs to the definition-list
        # property labelled exactly "摘要更新".  Other <time> elements in the
        # research report must not affect homepage recency.
        if self._pending_summary_update_index is not None:
            if tag == "dd":
                self._summary_update_dd_index = self._pending_summary_update_index
                self._pending_summary_update_index = None
            else:
                self._pending_summary_update_index = None
        if tag == "dt":
            self._dt_depth += 1
            if self._dt_depth == 1:
                self._dt_parts = []
        elif tag == "time" and self._summary_update_dd_index is not None:
            attr_map = {name.casefold(): value or "" for name, value in attrs}
            self.summary_update_datetimes[self._summary_update_dd_index].append(
                attr_map.get("datetime", "")
            )

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
        if tag == "dt" and self._dt_depth:
            self._dt_depth -= 1
            if self._dt_depth == 0:
                if _collapse_whitespace(self._dt_parts) == "摘要更新":
                    self.summary_update_datetimes.append([])
                    self._pending_summary_update_index = (
                        len(self.summary_update_datetimes) - 1
                    )
                self._dt_parts = []
        elif tag == "dd" and self._summary_update_dd_index is not None:
            self._summary_update_dd_index = None

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
        if self._dt_depth:
            self._dt_parts.append(data)
        if self._anchor_href is not None:
            self._anchor_parts.append(data)


class GeneratedDocumentParser(HTMLParser):
    """Collect generated URL-bearing attributes and local fragment targets."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.references: list[tuple[str, str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        normalized_tag = tag.casefold()
        for name, value in attrs:
            normalized_name = name.casefold()
            normalized_value = value or ""
            if normalized_name == "id":
                self.ids.append(normalized_value)
            if normalized_name in {"href", "src"}:
                self.references.append(
                    (normalized_tag, normalized_name, normalized_value)
                )


def _collapse_whitespace(parts: list[str]) -> str:
    return " ".join("".join(parts).split())


def _normalized_sort_key(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _summary_last_updated(parser: SummaryMetadataParser, path: Path) -> date:
    fields = parser.summary_update_datetimes
    if len(fields) != 1:
        raise BuildError(
            "Summary must contain exactly one <dt>摘要更新</dt> property followed "
            f"by a <dd> date: {path}"
        )
    if len(fields[0]) != 1:
        raise BuildError(
            "The 摘要更新 property must contain exactly one <time datetime=\"YYYY-MM-DD\">: "
            f"{path}"
        )

    raw_value = fields[0][0]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_value):
        raise BuildError(
            "The 摘要更新 datetime must use the exact YYYY-MM-DD format: "
            f"{path}"
        )
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise BuildError(
            f"The 摘要更新 datetime is not a valid calendar date in {path}: {raw_value}"
        ) from exc


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
        last_updated = _summary_last_updated(parser, relative_path)
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
                last_updated=last_updated,
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


def _rewrite_public_breadcrumb(
    document: str, paper: Paper, topic_route: str, subtopic_route: str
) -> str:
    breadcrumb_matches: list[re.Match[str]] = []
    for match in PARAGRAPH_ELEMENT_RE.finditer(document):
        class_match = CLASS_ATTRIBUTE_RE.search(match.group("attributes"))
        if class_match is None:
            continue
        class_tokens = {
            token.casefold() for token in class_match.group("value").split()
        }
        if "breadcrumb" in class_tokens:
            breadcrumb_matches.append(match)

    if len(breadcrumb_matches) != 1:
        raise BuildError(
            "Summary must contain exactly one template <p class=\"breadcrumb\"> "
            f"for public navigation: {paper.relative_directory}"
        )

    encoded_topic_route = _route_component(topic_route)
    encoded_subtopic_route = _route_component(subtopic_route)
    breadcrumb = (
        '<nav class="breadcrumb" aria-label="麵包屑">\n'
        '      <a href="../../">首頁</a>\n'
        '      <span aria-hidden="true">/</span>\n'
        '      <a href="../../library/">論文閱讀儲藏庫</a>\n'
        '      <span aria-hidden="true">/</span>\n'
        f'      <a href="../../library/{encoded_topic_route}/">'
        f"{html.escape(paper.topic)}</a>\n"
        '      <span aria-hidden="true">/</span>\n'
        f'      <a href="../../library/{encoded_topic_route}/'
        f'{encoded_subtopic_route}/">{html.escape(paper.subtopic)}</a>\n'
        '      <span aria-hidden="true">/</span>\n'
        f'      <span aria-current="page">{html.escape(paper.title)}</span>\n'
        "    </nav>"
    )
    match = breadcrumb_matches[0]
    return document[: match.start()] + breadcrumb + document[match.end() :]


def _rewrite_summary(
    document: str, paper: Paper, topic_route: str, subtopic_route: str
) -> str:
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
    rewritten = _rewrite_public_breadcrumb(
        rewritten, paper, topic_route, subtopic_route
    )
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


SITE_STYLE = """
    :root { color-scheme: light dark; --bg: #f4f6fb; --panel: #fff; --text: #172033; --muted: #647089; --line: #dce2ec; --accent: #3157d5; --accent-soft: #e9edff; --folder: #f1b84b; --folder-tab: #ffd77d; --shadow: 0 12px 32px rgb(16 24 40 / .07); }
    @media (prefers-color-scheme: dark) { :root { --bg: #10131b; --panel: #181d29; --text: #eef2ff; --muted: #aab3c7; --line: #30394c; --accent: #a9baff; --accent-soft: #252e50; --folder: #c68d29; --folder-tab: #e3b453; --shadow: 0 12px 32px rgb(0 0 0 / .25); } }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, "Segoe UI", sans-serif; line-height: 1.6; }
    a { color: var(--accent); }
    a:focus-visible, input:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
    .shell { width: min(1120px, calc(100% - 2rem)); margin: 0 auto; }
    .site-header { padding: 2.4rem 0 1.5rem; }
    .hero { padding-top: 4rem; }
    .breadcrumbs { display: flex; flex-wrap: wrap; gap: .4rem; margin: 0 0 1.4rem; color: var(--muted); font-size: .9rem; }
    .breadcrumbs a { color: inherit; }
    .eyebrow, .folder-kicker { margin: 0 0 .4rem; color: var(--accent); font-size: .76rem; font-weight: 780; letter-spacing: .1em; text-transform: uppercase; }
    h1 { margin: 0; font-size: clamp(2rem, 5vw, 3.5rem); line-height: 1.12; }
    h2 { margin: 0; font-size: clamp(1.35rem, 3vw, 1.8rem); }
    .intro { max-width: 48rem; margin: .8rem 0 0; color: var(--muted); }
    main { padding-bottom: 4rem; }
    .section-block { margin-top: 2.8rem; }
    .section-heading { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
    .section-heading p { margin: 0; color: var(--muted); font-size: .92rem; }
    .library-cta { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 1.1rem; margin-top: 2rem; border: 1px solid color-mix(in srgb, var(--accent) 35%, var(--line)); border-radius: 1.15rem; background: linear-gradient(135deg, var(--panel), var(--accent-soft)); color: var(--text); padding: 1.25rem 1.35rem; text-decoration: none; box-shadow: var(--shadow); }
    .library-cta:hover { border-color: var(--accent); transform: translateY(-1px); }
    .library-cta strong { display: block; font-size: 1.12rem; }
    .library-cta small { color: var(--muted); }
    .folder-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 245px), 1fr)); gap: 1rem; }
    .folder-card { display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 1rem; min-height: 8.3rem; border: 1px solid var(--line); border-radius: 1rem; background: var(--panel); color: var(--text); padding: 1.05rem; text-decoration: none; box-shadow: var(--shadow); }
    .folder-card:hover { border-color: var(--accent); transform: translateY(-2px); }
    .folder-card strong { display: block; line-height: 1.35; }
    .folder-card small { display: block; margin-top: .28rem; color: var(--muted); }
    .folder-icon { position: relative; display: inline-block; width: 3.4rem; height: 2.55rem; border-radius: .25rem .45rem .45rem .45rem; background: var(--folder); box-shadow: inset 0 -5px 0 rgb(0 0 0 / .08); }
    .folder-icon::before { position: absolute; left: 0; top: -.58rem; width: 1.7rem; height: .75rem; border-radius: .35rem .35rem 0 0; background: var(--folder-tab); content: ""; }
    .folder-icon.compact { width: 2.6rem; height: 1.95rem; }
    .folder-icon.compact::before { top: -.45rem; width: 1.3rem; height: .58rem; }
    .paper-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 1rem; }
    .paper-card { display: flex; min-height: 12rem; flex-direction: column; border: 1px solid var(--line); border-radius: 1rem; background: var(--panel); padding: 1.1rem; box-shadow: var(--shadow); }
    .paper-card h3 { margin: 0; font-size: 1.05rem; line-height: 1.45; }
    .paper-card h3 a { color: var(--text); text-decoration: none; }
    .paper-card h3 a:hover { color: var(--accent); text-decoration: underline; }
    .paper-meta { display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .8rem; color: var(--muted); font-size: .84rem; }
    .paper-date { margin: .65rem 0 0; color: var(--muted); font-size: .84rem; }
    .paper-actions { display: flex; flex-wrap: wrap; gap: .9rem; margin-top: auto; padding-top: 1rem; font-weight: 700; font-size: .9rem; }
    .source-link { color: var(--muted); font-weight: 600; }
    .search-box { max-width: 44rem; margin-top: 1.5rem; }
    .search-box label { display: block; margin-bottom: .45rem; font-weight: 700; }
    .search-box input { width: 100%; border: 1px solid var(--line); border-radius: .8rem; background: var(--panel); color: var(--text); padding: .85rem 1rem; font: inherit; }
    #result-status { margin: .55rem 0 0; color: var(--muted); font-size: .92rem; }
    .empty-state { border: 1px dashed var(--line); border-radius: .9rem; color: var(--muted); padding: 1rem; text-align: center; }
    [hidden] { display: none !important; }
    @media (max-width: 560px) { .hero { padding-top: 2.5rem; } .library-cta { grid-template-columns: auto 1fr; } .library-cta .cta-arrow { display: none; } .section-heading { align-items: start; flex-direction: column; } }
    @media (prefers-reduced-motion: no-preference) { .library-cta, .folder-card { transition: border-color .16s ease, transform .16s ease; } }
"""


def _paper_taxonomy_key(paper: Paper) -> tuple[str, str, str, str]:
    return (
        _normalized_sort_key(paper.topic),
        _normalized_sort_key(paper.subtopic),
        _normalized_sort_key(paper.title),
        _normalized_sort_key(paper.relative_directory.as_posix()),
    )


def _paper_recency_key(paper: Paper) -> tuple[int, str, str, str, str]:
    return (-paper.last_updated.toordinal(), *_paper_taxonomy_key(paper))


def _group_papers(
    papers: list[Paper],
) -> dict[str, dict[str, list[Paper]]]:
    grouped: dict[str, dict[str, list[Paper]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for paper in papers:
        grouped[paper.topic][paper.subtopic].append(paper)
    return grouped


def _folder_route_slug(label: str, identity: str) -> str:
    normalized_label = unicodedata.normalize("NFKC", label).casefold()
    parts: list[str] = []
    saw_separator = False
    for character in normalized_label:
        if character.isalnum():
            if saw_separator and parts:
                parts.append("-")
            parts.append(character)
            saw_separator = False
        else:
            saw_separator = True
    # Keep two nested route components below Windows' legacy MAX_PATH while the
    # digest retains collision resistance for punctuation and Unicode variants.
    readable = "".join(parts).strip("-")[:12].rstrip("-") or "folder"
    digest_input = unicodedata.normalize("NFKC", identity).encode("utf-8")
    digest = hashlib.sha256(digest_input).hexdigest()[:10]
    return f"{readable}-{digest}"


def _library_routes(
    grouped: dict[str, dict[str, list[Paper]]],
) -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    topic_routes: dict[str, str] = {}
    subtopic_routes: dict[tuple[str, str], str] = {}
    used_topic_routes: dict[str, str] = {}

    for topic in sorted(grouped, key=_normalized_sort_key):
        topic_route = _folder_route_slug(topic, f"topic\0{topic}")
        previous_topic = used_topic_routes.get(topic_route.casefold())
        if previous_topic is not None and previous_topic != topic:
            raise BuildError(
                f"Topic folders resolve to the same route: {previous_topic!r} and {topic!r}"
            )
        used_topic_routes[topic_route.casefold()] = topic
        topic_routes[topic] = topic_route

        used_subtopic_routes: dict[str, str] = {}
        for subtopic in sorted(grouped[topic], key=_normalized_sort_key):
            subtopic_route = _folder_route_slug(
                subtopic, f"subtopic\0{topic}\0{subtopic}"
            )
            previous_subtopic = used_subtopic_routes.get(subtopic_route.casefold())
            if previous_subtopic is not None and previous_subtopic != subtopic:
                raise BuildError(
                    "Subtopic folders resolve to the same route under "
                    f"{topic!r}: {previous_subtopic!r} and {subtopic!r}"
                )
            used_subtopic_routes[subtopic_route.casefold()] = subtopic
            subtopic_routes[(topic, subtopic)] = subtopic_route

    return topic_routes, subtopic_routes


def _route_component(value: str) -> str:
    return quote(value, safe="-")


def _display_date(value: date) -> str:
    return f"{value.year} 年 {value.month} 月 {value.day} 日"


def _render_page(*, title: str, description: str, content: str, script: str = "") -> str:
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, noarchive">
  <meta name="description" content="{html.escape(description, quote=True)}">
  <title>{html.escape(title)}</title>
  <style>{SITE_STYLE}</style>
</head>
<body>
{content}
{script}
</body>
</html>
"""


def _source_link(paper: Paper) -> str:
    if paper.source is None:
        return ""
    return (
        '<a class="source-link" href="'
        + html.escape(paper.source.url, quote=True)
        + '" target="_blank" rel="noopener noreferrer">原始來源 ↗</a>'
    )


def _render_paper_card(
    paper: Paper,
    *,
    paper_href: str,
    latest: bool = False,
    searchable: bool = False,
    drilldown: bool = False,
) -> str:
    article_attributes = ['class="paper-card"']
    if latest:
        article_attributes.append(
            f'data-latest-paper="{html.escape(paper.slug, quote=True)}"'
        )
    if searchable:
        search_text = " ".join(
            (paper.topic, paper.subtopic, paper.title, paper.directory_name)
        )
        article_attributes.extend(
            ("data-paper", f'data-search="{html.escape(search_text, quote=True)}"')
        )
    link_attribute = (
        ' data-folder-kind="paper" data-paper-slug="'
        + html.escape(paper.slug, quote=True)
        + '"'
        if drilldown
        else ""
    )
    escaped_href = html.escape(paper_href, quote=True)
    return (
        f"<article {' '.join(article_attributes)}>"
        f'<h3><a{link_attribute} href="{escaped_href}">{html.escape(paper.title)}</a></h3>'
        '<div class="paper-meta">'
        f"<span>{html.escape(paper.topic)}</span>"
        '<span aria-hidden="true">›</span>'
        f"<span>{html.escape(paper.subtopic)}</span>"
        "</div>"
        '<p class="paper-date">摘要更新：'
        f'<time datetime="{paper.last_updated.isoformat()}">{_display_date(paper.last_updated)}</time>'
        "</p>"
        f'<div class="paper-actions"><a href="{escaped_href}">閱讀摘要</a>'
        f"{_source_link(paper)}</div>"
        "</article>"
    )


def _folder_card(
    *, href: str, kicker: str, title: str, detail: str, attributes: str
) -> str:
    return (
        f'<a class="folder-card" {attributes} href="{html.escape(href, quote=True)}">'
        '<span class="folder-icon" aria-hidden="true"></span>'
        '<span><span class="folder-kicker">'
        f"{html.escape(kicker)}</span><strong>{html.escape(title)}</strong>"
        f"<small>{html.escape(detail)}</small></span></a>"
    )


def _render_home(
    papers: list[Paper],
    grouped: dict[str, dict[str, list[Paper]]],
    topic_routes: dict[str, str],
    subtopic_routes: dict[tuple[str, str], str],
) -> str:
    latest_papers = sorted(papers, key=_paper_recency_key)[:3]
    recent_folders: list[tuple[date, str, str, list[Paper]]] = []
    for topic in sorted(grouped, key=_normalized_sort_key):
        for subtopic in sorted(grouped[topic], key=_normalized_sort_key):
            children = grouped[topic][subtopic]
            recent_folders.append(
                (max(paper.last_updated for paper in children), topic, subtopic, children)
            )
    recent_folders.sort(
        key=lambda item: (
            -item[0].toordinal(),
            _normalized_sort_key(item[1]),
            _normalized_sort_key(item[2]),
        )
    )

    recent_cards: list[str] = []
    for newest, topic, subtopic, children in recent_folders[:3]:
        topic_route = _route_component(topic_routes[topic])
        subtopic_route = _route_component(subtopic_routes[(topic, subtopic)])
        attributes = (
            "data-recent-folder "
            f'data-topic="{html.escape(topic, quote=True)}" '
            f'data-subtopic="{html.escape(subtopic, quote=True)}"'
        )
        recent_cards.append(
            _folder_card(
                href=f"library/{topic_route}/{subtopic_route}/",
                kicker=topic,
                title=subtopic,
                detail=f"{len(children)} 篇 · 最近更新 {_display_date(newest)}",
                attributes=attributes,
            )
        )

    latest_cards = [
        _render_paper_card(
            paper, paper_href=f"papers/{paper.slug}/", latest=True
        )
        for paper in latest_papers
    ]
    content = f"""  <header class="site-header hero shell">
    <p class="eyebrow">Paper Reading</p>
    <h1>論文閱讀首頁</h1>
    <p class="intro">把近期研究焦點、最新完成的深度閱讀，以及依 Topic／Subtopic 整理的完整儲藏庫放在同一個入口。</p>
    <a class="library-cta" href="library/">
      <span class="folder-icon compact" aria-hidden="true"></span>
      <span><strong>論文閱讀儲藏庫</strong><small>{len(papers)} 篇論文 · {len(grouped)} 個 Topic</small></span>
      <span class="cta-arrow" aria-hidden="true">進入儲藏庫 →</span>
    </a>
  </header>
  <main class="shell">
    <section class="section-block" aria-labelledby="recent-topics-heading">
      <div class="section-heading"><h2 id="recent-topics-heading">最近關注的主題</h2><p>依子題中最新完成的摘要排序</p></div>
      <div class="folder-grid">{''.join(recent_cards)}</div>
    </section>
    <section class="section-block" aria-labelledby="latest-papers-heading">
      <div class="section-heading"><h2 id="latest-papers-heading">最新三篇論文閱讀</h2><p>依摘要更新日期排序</p></div>
      <div class="paper-grid">{''.join(latest_cards)}</div>
    </section>
  </main>"""
    return _render_page(
        title="Paper Reading｜論文閱讀首頁",
        description="近期研究主題、最新三篇論文閱讀與完整論文儲藏庫",
        content=content,
    )


def _render_library_index(
    papers: list[Paper],
    grouped: dict[str, dict[str, list[Paper]]],
    topic_routes: dict[str, str],
) -> str:
    topic_cards: list[str] = []
    for topic in sorted(grouped, key=_normalized_sort_key):
        topic_papers = [
            paper for subtopic in grouped[topic].values() for paper in subtopic
        ]
        newest = max(paper.last_updated for paper in topic_papers)
        topic_cards.append(
            _folder_card(
                href=f"{_route_component(topic_routes[topic])}/",
                kicker="Topic",
                title=topic,
                detail=(
                    f"{len(grouped[topic])} 個 Subtopic · {len(topic_papers)} 篇 · "
                    f"更新 {_display_date(newest)}"
                ),
                attributes=(
                    'data-folder-kind="topic" data-topic="'
                    + html.escape(topic, quote=True)
                    + '"'
                ),
            )
        )

    paper_cards = [
        _render_paper_card(
            paper,
            paper_href=f"../papers/{paper.slug}/",
            searchable=True,
        )
        for paper in sorted(papers, key=_paper_taxonomy_key)
    ]
    content = f"""  <header class="site-header shell">
    <nav class="breadcrumbs" aria-label="麵包屑"><a href="../">首頁</a><span aria-hidden="true">/</span><span aria-current="page">論文閱讀儲藏庫</span></nav>
    <p class="eyebrow">Library</p>
    <h1>論文閱讀儲藏庫</h1>
    <p class="intro">先從 Topic 資料夾逐層瀏覽，或直接搜尋所有繁體中文深度閱讀摘要。</p>
    <div class="search-box">
      <label for="paper-search">搜尋全部論文</label>
      <input id="paper-search" type="search" placeholder="例如：KV cache、serving、Prefill" autocomplete="off">
      <p id="result-status" role="status" aria-live="polite">共 {len(papers)} 篇</p>
    </div>
  </header>
  <main class="shell">
    <section aria-labelledby="topics-heading">
      <div class="section-heading"><h2 id="topics-heading">Topic 資料夾</h2><p>{len(grouped)} 個 Topic</p></div>
      <div class="folder-grid">{''.join(topic_cards)}</div>
    </section>
    <section class="section-block" aria-labelledby="all-papers-heading">
      <div class="section-heading"><h2 id="all-papers-heading">全部論文</h2><p>搜尋會比對 Topic、Subtopic 與標題</p></div>
      <div class="paper-grid" id="paper-list">{''.join(paper_cards)}</div>
      <p class="empty-state" id="empty-state" hidden>找不到符合條件的論文。</p>
    </section>
  </main>"""
    script = """  <script>
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
        status.textContent = terms.length ? `顯示 ${visible} / ${papers.length} 篇` : `共 ${papers.length} 篇`;
        empty.hidden = visible !== 0;
      };
      input.addEventListener("input", update);
    })();
  </script>"""
    return _render_page(
        title="論文閱讀儲藏庫｜Paper Reading",
        description="依 Topic 與 Subtopic 瀏覽或搜尋繁體中文論文閱讀摘要",
        content=content,
        script=script,
    )


def _render_topic_page(
    topic: str,
    subtopics: dict[str, list[Paper]],
    subtopic_routes: dict[tuple[str, str], str],
) -> str:
    cards: list[str] = []
    for subtopic in sorted(subtopics, key=_normalized_sort_key):
        children = subtopics[subtopic]
        newest = max(paper.last_updated for paper in children)
        cards.append(
            _folder_card(
                href=f"{_route_component(subtopic_routes[(topic, subtopic)])}/",
                kicker="Subtopic",
                title=subtopic,
                detail=f"{len(children)} 篇 · 更新 {_display_date(newest)}",
                attributes=(
                    'data-folder-kind="subtopic" data-topic="'
                    + html.escape(topic, quote=True)
                    + '" data-subtopic="'
                    + html.escape(subtopic, quote=True)
                    + '"'
                ),
            )
        )
    paper_count = sum(len(children) for children in subtopics.values())
    content = f"""  <header class="site-header shell">
    <nav class="breadcrumbs" aria-label="麵包屑"><a href="../../">首頁</a><span aria-hidden="true">/</span><a href="../">論文閱讀儲藏庫</a><span aria-hidden="true">/</span><span aria-current="page">{html.escape(topic)}</span></nav>
    <p class="eyebrow">Topic</p>
    <h1>{html.escape(topic)}</h1>
    <p class="intro">{len(subtopics)} 個 Subtopic，共 {paper_count} 篇論文閱讀。</p>
  </header>
  <main class="shell">
    <section aria-labelledby="subtopics-heading">
      <div class="section-heading"><h2 id="subtopics-heading">Subtopic 資料夾</h2><p>選擇資料夾繼續瀏覽</p></div>
      <div class="folder-grid">{''.join(cards)}</div>
    </section>
  </main>"""
    return _render_page(
        title=f"{topic}｜論文閱讀儲藏庫",
        description=f"{topic} Topic 下的論文閱讀 Subtopic",
        content=content,
    )


def _render_subtopic_page(topic: str, subtopic: str, papers: list[Paper]) -> str:
    cards = [
        _render_paper_card(
            paper,
            paper_href=f"../../../papers/{paper.slug}/",
            drilldown=True,
        )
        for paper in sorted(papers, key=_paper_recency_key)
    ]
    content = f"""  <header class="site-header shell">
    <nav class="breadcrumbs" aria-label="麵包屑"><a href="../../../">首頁</a><span aria-hidden="true">/</span><a href="../../">論文閱讀儲藏庫</a><span aria-hidden="true">/</span><a href="../">{html.escape(topic)}</a><span aria-hidden="true">/</span><span aria-current="page">{html.escape(subtopic)}</span></nav>
    <p class="eyebrow">Subtopic</p>
    <h1>{html.escape(subtopic)}</h1>
    <p class="intro">{html.escape(topic)} 下共 {len(papers)} 篇論文閱讀，依摘要更新日期排列。</p>
  </header>
  <main class="shell">
    <section aria-labelledby="papers-heading">
      <div class="section-heading"><h2 id="papers-heading">論文</h2><p>選擇論文開啟完整摘要</p></div>
      <div class="paper-grid">{''.join(cards)}</div>
    </section>
  </main>"""
    return _render_page(
        title=f"{subtopic}｜{topic}｜論文閱讀儲藏庫",
        description=f"{topic} / {subtopic} 下的繁體中文論文閱讀摘要",
        content=content,
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


def _validate_generated_references(site_directory: Path) -> None:
    """Fail closed unless every generated href/src resolves safely."""

    site_root = site_directory.resolve()
    documents: dict[Path, GeneratedDocumentParser] = {}
    for document_path in sorted(
        site_directory.rglob("*.html"),
        key=lambda path: _normalized_sort_key(
            path.relative_to(site_directory).as_posix()
        ),
    ):
        try:
            document = document_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise BuildError(
                f"Generated HTML is not valid UTF-8: {document_path}"
            ) from exc
        parser = GeneratedDocumentParser()
        parser.feed(document)
        parser.close()
        duplicate_ids = sorted(
            {identifier for identifier in parser.ids if parser.ids.count(identifier) > 1},
            key=_normalized_sort_key,
        )
        if duplicate_ids:
            relative_path = document_path.relative_to(site_directory)
            raise BuildError(
                f"Generated HTML contains ambiguous duplicate id {duplicate_ids[0]!r}: "
                f"{relative_path}"
            )
        documents[document_path.resolve()] = parser

    for document_path in sorted(
        documents,
        key=lambda path: _normalized_sort_key(path.relative_to(site_root).as_posix()),
    ):
        parser = documents[document_path]
        relative_document = document_path.relative_to(site_root)
        for tag, attribute, raw_reference in parser.references:
            reference = raw_reference.strip()
            context = f"{relative_document} <{tag}> {attribute}={raw_reference!r}"
            if not reference or reference != raw_reference:
                raise BuildError(f"Generated URL is empty or padded with whitespace: {context}")
            if any(ord(character) < 0x20 or ord(character) == 0x7F for character in reference):
                raise BuildError(f"Generated URL contains a control character: {context}")
            if "\\" in reference:
                raise BuildError(f"Generated URL contains a backslash: {context}")
            if INVALID_PERCENT_ESCAPE_RE.search(reference):
                raise BuildError(f"Generated URL has invalid percent encoding: {context}")

            try:
                parsed = urlsplit(reference)
            except ValueError as exc:
                raise BuildError(f"Generated URL cannot be parsed: {context}") from exc

            if tag == "base":
                raise BuildError(f"Generated HTML must not override its base URL: {context}")
            scheme = parsed.scheme.casefold()
            if scheme:
                if scheme not in {"http", "https"} or not parsed.netloc:
                    raise BuildError(f"Generated URL uses an unsafe scheme: {context}")
                continue
            if parsed.netloc or reference.startswith("//"):
                raise BuildError(f"Generated URL is protocol-relative: {context}")

            decoded_path = unquote(parsed.path)
            if "%" in decoded_path:
                raise BuildError(
                    f"Generated local URL contains nested percent encoding: {context}"
                )
            if decoded_path.startswith(("/", "\\")) or "\\" in decoded_path:
                raise BuildError(f"Generated local URL is root-relative: {context}")
            if any(
                ord(character) < 0x20 or ord(character) == 0x7F
                for character in decoded_path
            ):
                raise BuildError(
                    f"Generated local URL decodes to a control character: {context}"
                )

            path_parts = PurePosixPath(decoded_path).parts if decoded_path else ()
            try:
                target = document_path.parent.joinpath(*path_parts).resolve()
                target.relative_to(site_root)
            except (OSError, ValueError) as exc:
                raise BuildError(f"Generated local URL escapes _site: {context}") from exc

            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                raise BuildError(
                    f"Generated local URL target does not exist: {context} -> {target}"
                )

            has_fragment_delimiter = "#" in reference
            if has_fragment_delimiter and not parsed.fragment:
                raise BuildError(f"Generated URL has an empty fragment: {context}")
            if not parsed.fragment:
                continue
            if INVALID_PERCENT_ESCAPE_RE.search(parsed.fragment):
                raise BuildError(f"Generated fragment has invalid encoding: {context}")
            fragment = unquote(parsed.fragment)
            if "%" in fragment or not fragment:
                raise BuildError(f"Generated fragment is invalid: {context}")
            target_parser = documents.get(target.resolve())
            if target_parser is None:
                raise BuildError(
                    f"Generated fragment targets a non-HTML document: {context}"
                )
            if fragment not in set(target_parser.ids):
                raise BuildError(
                    f"Generated fragment target #{fragment} does not exist: {context}"
                )


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
    grouped = _group_papers(papers)
    topic_routes, subtopic_routes = _library_routes(grouped)
    staging_directory = output_directory.with_name(
        f"{OUTPUT_DIRECTORY_NAME}.__building__"
    )
    _safe_remove_build_directory(staging_directory, root)
    staging_directory.mkdir(parents=True)

    try:
        for paper in papers:
            document = paper.summary_path.read_text(encoding="utf-8")
            rewritten = _rewrite_summary(
                document,
                paper,
                topic_routes[paper.topic],
                subtopic_routes[(paper.topic, paper.subtopic)],
            )
            paper_output = staging_directory / "papers" / paper.slug
            paper_output.mkdir(parents=True)
            (paper_output / "index.html").write_text(
                rewritten, encoding="utf-8", newline="\n"
            )
            _copy_assets(paper.summary_path.parent, paper_output, paper.image_paths)

        (staging_directory / "index.html").write_text(
            _render_home(
                papers, grouped, topic_routes, subtopic_routes
            ),
            encoding="utf-8",
            newline="\n",
        )

        library_directory = staging_directory / "library"
        library_directory.mkdir()
        (library_directory / "index.html").write_text(
            _render_library_index(papers, grouped, topic_routes),
            encoding="utf-8",
            newline="\n",
        )
        for topic in sorted(grouped, key=_normalized_sort_key):
            topic_directory = library_directory / topic_routes[topic]
            topic_directory.mkdir()
            (topic_directory / "index.html").write_text(
                _render_topic_page(topic, grouped[topic], subtopic_routes),
                encoding="utf-8",
                newline="\n",
            )
            for subtopic in sorted(grouped[topic], key=_normalized_sort_key):
                subtopic_directory = (
                    topic_directory / subtopic_routes[(topic, subtopic)]
                )
                subtopic_directory.mkdir()
                (subtopic_directory / "index.html").write_text(
                    _render_subtopic_page(
                        topic, subtopic, grouped[topic][subtopic]
                    ),
                    encoding="utf-8",
                    newline="\n",
                )
        (staging_directory / ".nojekyll").write_text(
            "", encoding="utf-8", newline="\n"
        )
        _validate_generated_references(staging_directory)
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
