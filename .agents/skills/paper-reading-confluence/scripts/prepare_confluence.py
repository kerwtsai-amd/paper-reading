#!/usr/bin/env python3
"""Validate a paper-reading Markdown draft and render Confluence storage XHTML.

The regular Markdown conversion is delegated to the installed slai-atlassian
skill so this helper stays aligned with the CLI that will publish the page. This
script only adds the paper-specific contract and attachment directives.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
import re
import sys
import tempfile
import unicodedata
from datetime import date
from unittest import mock
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any, Iterable, Optional


TEMPLATE_MARKER = "<!-- paper-reading-confluence-template:v1 -->"
STORAGE_GENERATOR_MARKER = "<!-- generated-by:paper-reading-confluence/v1 -->"
NO_IMAGE_MARKER = "**[分析]** 本摘要未擷取圖表："
NO_IMAGE_ABSENCE_MARKER = "**[作者主張]** 論文未提供圖表"
EXPECTED_SECTIONS = [
    "論文基本資料",
    "一句話總結",
    "Executive Summary",
    "背景與動機",
    "問題定義",
    "核心方法",
    "公式與理論",
    "圖片與圖表導讀",
    "實驗設計",
    "實驗結果",
    "Ablation 與敏感度分析",
    "優點、限制與風險",
    "與相關工作的比較",
    "個人分析與可延伸方向",
    "組會討論問題",
    "術語表與重點索引",
]
METADATA_FIELDS = [
    "欄位",
    "正式標題",
    "作者",
    "出處／版本",
    "年份",
    "分類",
    "分類理由",
    "頁數",
    "最後更新",
]

DIRECTIVE_RE = re.compile(
    r"(?ms)^[ \t]*```(paper-image|paper-attachment)[ \t]*\r?\n"
    r"(.*?)\r?\n[ \t]*```[ \t]*$"
)
PLACEHOLDER_RE = re.compile(r"\{\{[^{}\r\n]+\}\}")
PAGE_COUNT_RE = re.compile(r"共\s*[1-9]\d*\s*頁")
MARKDOWN_IMAGE_RE = re.compile(
    r"!\[[^\]\r\n]*\](?:\([^\r\n)]*\)|\[[^\]\r\n]*\])?"
)
WINDOWS_PATH_RE = re.compile(
    r"(?i)(?:\b[A-Z]:[\\/]|\\\\\?\\|\\\\\.\\|(?<!:)(?:\\\\|//)[^\\/\s]+[\\/][^\\/\s]+)"
)
POSIX_PATH_RE = re.compile(
    r"(?<![:/A-Za-z0-9._-])/(?!/)[^/\s<>()\[\]{}，、。；！？]+"
    r"(?:/[^/\s<>()\[\]{}，、。；！？]+)*"
)
FILESYSTEM_ROOTS = {
    "bin",
    "boot",
    "data",
    "dev",
    "etc",
    "home",
    "lib",
    "lib64",
    "media",
    "mnt",
    "opt",
    "proc",
    "root",
    "run",
    "sbin",
    "srv",
    "sys",
    "tmp",
    "usr",
    "var",
    "workspace",
}
API_ROUTE_ROOTS = {"api", "generate", "graphql", "health", "healthz", "metrics"}
HTTP_METHOD_PREFIX_RE = re.compile(
    r"(?:^|\s)(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+$", re.I
)
PATH_CUE_RE = re.compile(
    r"(?:位於|路徑|檔案|目錄|資料夾|儲存(?:於|至)?|寫入(?:至|到)?|讀取自)$"
)
NESTED_PAREN_LINK_RE = re.compile(r"(?<!\!)\[[^\]\r\n]*\]\([^\r\n)]*\(")
RAW_HTML_RE = re.compile(
    r"(?is)(?:<!--.*?-->|<!DOCTYPE\b[^>]*>|</?[A-Za-z][\w:.-]*\b[^<>]*>)"
)
OBJECT_LABEL_PATTERN = (
    r"(?:Figure|Table|Algorithm)\s+"
    r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*(?:\s*\([A-Za-z0-9]+\))?"
)
OBJECT_LABEL_RE = re.compile(
    rf"(?<![\w])({OBJECT_LABEL_PATTERN})(?![\w])"
)
EVIDENCE_LABEL_RE = re.compile(r"\*\*\[(作者主張|實驗事實|分析|推測)\]\*\*")
SOURCE_LOCATOR_RE = re.compile(
    r"(?:§\s*(?:\d+(?:\.\d+)*(?![\w.])|[A-Za-z][A-Za-z0-9.-]*(?![\w.]))"
    r"|\b(?:Section|Sec\.)\s+[A-Za-z0-9][A-Za-z0-9.-]*"
    r"|\b(?:Abstract|Introduction|Conclusion)\b"
    r"|\bAppendix\s+[A-Za-z0-9][A-Za-z0-9.-]*"
    r"|附錄\s*[A-Za-z0-9一二三四五六七八九十]+)",
    re.I,
)
PDF_SOURCE_RE = re.compile(r"(?<![\w])PDF\s+p\.\s*[1-9]\d*(?![\w])", re.I)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])\s*|\n+")
NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:\s*(?:%|×|x\b|倍))?", re.I)
XML_INVALID_RE = re.compile(
    "[\x00-\x08\x0B\x0C\x0E-\x1F\uD800-\uDFFF\uFFFE\uFFFF]"
)

FORBIDDEN_VISIBLE_PATTERNS = {
    "PDF intake 結果": re.compile(r"(?i)PDF\s+(?:signature|hash)\s*(?:valid|verified|通過|有效)"),
    "credential 名稱": re.compile(r"(?i)ATLASSIAN_(?:SITE|EMAIL|API_TOKEN)"),
    "作業驗證結果": re.compile(
        r"(?i)(?:(?:PDF|附件|Confluence|storage\s+XHTML|摘要檔|來源稿|圖片檔|"
        r"上傳作業|下載作業|渲染作業|QA).{0,16}(?:驗證|檢查|下載|上傳|渲染)"
        r".{0,8}(?:成功|完成|通過)|QA\s*(?:passed|completed|通過|完成))"
    ),
    "產製路徑說明": re.compile(r"(?:絕對路徑|檔案命名理由|Windows\s*禁止字元|裁圖命令)"),
    "附件產製紀錄": re.compile(
        r"(?:本圖\s*(?:裁切|擷取|上傳)自|(?:裁切|擷取|上傳)自\s*(?:原論文|PDF|本機|本地檔案))",
        re.I,
    ),
}


class DraftError(Exception):
    """Raised when a source draft violates the publishing contract."""


@dataclass(frozen=True)
class Directive:
    kind: str
    data: dict[str, Any]
    local_path: Path
    attachment_name: str
    token: str


@dataclass
class SemanticSummary:
    headings: list[tuple[str, str]]
    h1_count: int
    other_heading_count: int
    content_counts: dict[int, int]
    prose_units: dict[int, list[str]]
    table_rows: dict[int, list[list[str]]]
    list_item_counts: dict[int, int]
    directive_sections: list[tuple[str, Optional[int]]]
    preface_units: list[str]
    code_units: list[str]
    claim_units: dict[int, list[str]]


def _inline_plain(text: str, markup: ModuleType, *, omit_code: bool = False) -> str:
    """Return reader-visible inline text using the publisher's own parser."""
    return "".join(
        span["text"]
        for span in markup.parse_inline(text)
        if not (omit_code and "code" in span.get("marks", []))
    )


def _contains_material_number(statement: str) -> bool:
    """Detect numbers other than source/object locators and canonical URLs."""
    scrubbed = re.sub(r"https://\S+", "", statement, flags=re.I)
    scrubbed = PDF_SOURCE_RE.sub("", scrubbed)
    scrubbed = SOURCE_LOCATOR_RE.sub("", scrubbed)
    scrubbed = OBJECT_LABEL_RE.sub("", scrubbed)
    return NUMBER_RE.search(scrubbed) is not None


def _is_source_only(statement: str) -> bool:
    match = re.match(r"^[\s（(]*來源\s*[:：]", statement)
    if match is None:
        return False
    closing = max(statement.rfind("）"), statement.rfind(")"))
    if closing >= 0 and statement[closing + 1 :].strip(" \t。！？!?；;，,"):
        return False
    source_body = statement[match.end() : closing if closing >= 0 else None]
    source_body = PDF_SOURCE_RE.sub("", source_body)
    source_body = SOURCE_LOCATOR_RE.sub("", source_body)
    source_body = OBJECT_LABEL_RE.sub("", source_body)
    source_body = re.sub(
        r"(?<![\w])(?:Equation|Eq\.)\s+[A-Za-z0-9][A-Za-z0-9.()-]*(?![\w])",
        "",
        source_body,
        flags=re.I,
    )
    return not source_body.strip(" \t·•,，:：;；./。！？!?（）()[]")


def _contains_posix_path(text: str, *, allow_api_endpoint: bool = False) -> bool:
    for match in POSIX_PATH_RE.finditer(text):
        candidate = match.group(0)
        endpoint = candidate.rstrip(".,;:!?。；，、'\"")
        route_path = re.split(r"[?#]", endpoint, maxsplit=1)[0]
        components = [part for part in route_path.lstrip("/").split("/") if part]
        first_component = components[0].casefold() if components else ""
        prefix = text[max(0, match.start() - 24) : match.start()]

        if allow_api_endpoint:
            route_syntax = re.fullmatch(
                r"/[A-Za-z0-9._~:%-]+(?:/[A-Za-z0-9._~:%-]+)*(?:[?#][^\s]*)?",
                endpoint,
            )
            versioned_root = re.fullmatch(r"v\d+", first_component, re.I) is not None
            if route_syntax and (
                HTTP_METHOD_PREFIX_RE.search(prefix)
                or first_component in API_ROUTE_ROOTS
                or versioned_root
            ):
                # API routes are reader content, not local paths. An HTTP verb
                # makes arbitrary routes unambiguous; a few conventional roots
                # also cover standalone snippets such as /healthz and /graphql.
                continue

        previous = text[match.start() - 1] if match.start() else ""
        previous_is_cjk = "\u3400" <= previous <= "\u9fff"
        lexical_components = bool(components) and all(
            re.fullmatch(r"[\w~-]+", component, re.UNICODE)
            for component in components
        )
        has_path_signal = (
            first_component in FILESYSTEM_ROOTS
            or any("." in component for component in components)
            or any(component in {".", ".."} for component in components)
        )
        if (
            previous_is_cjk
            and lexical_components
            and not PATH_CUE_RE.search(prefix)
            and not has_path_signal
        ):
            # Slash-delimited Chinese prose and bilingual terms, such as
            # 讀取/寫入/同步 and 效能/performance, are not absolute paths.
            continue
        return True
    return False


def _is_not_provided_only(statement: str) -> bool:
    return re.fullmatch(r"\s*論文未提供[。.\s]*", statement) is not None


def _folder_matches_formal_title(formal_title: str, folder_name: str) -> bool:
    """Allow substitutions only where Windows forbids the formal title's character."""
    formal = unicodedata.normalize("NFKC", formal_title).casefold().rstrip(" .")
    folder = unicodedata.normalize("NFKC", folder_name).casefold().rstrip(" .")
    forbidden = re.compile(r'[<>:"/\\|?*]+')
    if not forbidden.search(formal):
        return folder == formal
    parts = forbidden.split(formal)
    pattern = r"[\s._-]*".join(re.escape(part) for part in parts)
    return re.fullmatch(pattern, folder) is not None


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _read_prefix(path: Path, length: int = 16) -> bytes:
    with path.open("rb") as handle:
        return handle.read(length)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise DraftError(f"無法計算附件內容雜湊：{path.name}：{exc}") from exc
    return digest.hexdigest()


def _pdf_page_count(path: Path) -> int:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DraftError("缺少 pypdf，無法核對 metadata 的 PDF 頁數") from exc
    try:
        return len(PdfReader(str(path)).pages)
    except Exception as exc:  # pypdf exposes several parser-specific exceptions.
        raise DraftError(f"無法讀取 PDF 頁數：{path.name}：{exc}") from exc


def _check_file(path: Path, kind: str, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"{kind} 不存在：{path}")
        return
    if path.stat().st_size == 0:
        errors.append(f"{kind} 是空檔：{path}")
        return

    prefix = _read_prefix(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf" and not prefix.startswith(b"%PDF-"):
        errors.append(f"PDF signature 無效：{path.name}")
    elif suffix == ".png" and not prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        errors.append(f"PNG signature 無效：{path.name}")
    elif suffix in {".jpg", ".jpeg"} and not prefix.startswith(b"\xff\xd8\xff"):
        errors.append(f"JPEG signature 無效：{path.name}")


def _require_text(data: dict[str, Any], key: str, label: str, errors: list[str]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} 的 `{key}` 必須是非空字串")
        return ""
    return value.strip()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"重複欄位 `{key}`")
        result[key] = value
    return result


def _parse_directives(text: str, paper_dir: Path, errors: list[str]) -> list[Directive]:
    directives: list[Directive] = []
    starts = len(re.findall(r"(?m)^[ \t]*```paper-(?:image|attachment)\b", text))
    matches = list(DIRECTIVE_RE.finditer(text))
    if starts != len(matches):
        errors.append("至少一個 paper-image／paper-attachment block 未正確關閉或不是有效 fenced block")

    for index, match in enumerate(matches):
        kind = match.group(1)
        label = f"{kind} block #{index + 1}"
        try:
            data = json.loads(match.group(2), object_pairs_hook=_reject_duplicate_keys)
        except json.JSONDecodeError as exc:
            errors.append(f"{label} 不是有效 JSON：line {exc.lineno}, column {exc.colno}")
            continue
        except ValueError as exc:
            errors.append(f"{label} 不是有效 JSON object：{exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{label} 必須是 JSON object")
            continue

        if kind == "paper-attachment":
            allowed = {"file", "label", "description"}
            unknown = sorted(set(data) - allowed)
            if unknown:
                errors.append(f"{label} 含未知欄位：{', '.join(unknown)}")
            file_value = _require_text(data, "file", label, errors)
            link_label = _require_text(data, "label", label, errors)
            if link_label and link_label != "開啟論文 PDF":
                errors.append(f"{label} 的 `label` 必須使用中性固定文字「開啟論文 PDF」")
            description = data.get("description")
            if description is not None and not isinstance(description, str):
                errors.append(f"{label} 的 `description` 必須是字串")

            if file_value:
                if Path(file_value).name != file_value or "/" in file_value or "\\" in file_value:
                    errors.append(f"{label} 的 `file` 只能是論文資料夾根層的 PDF basename")
                if Path(file_value).suffix.lower() != ".pdf":
                    errors.append(f"{label} 的 `file` 必須是 .pdf")
                local_path = (paper_dir / file_value).resolve()
            else:
                local_path = paper_dir / "__invalid__.pdf"
            if not _is_within(local_path, paper_dir):
                errors.append(f"{label} 的 `file` 不可離開論文資料夾")
            _check_file(local_path, "PDF attachment", errors)
            attachment_name = Path(file_value).name if file_value else "__invalid__.pdf"

        else:
            allowed = {"file", "label", "evidence", "alt", "guide", "source", "width"}
            unknown = sorted(set(data) - allowed)
            if unknown:
                errors.append(f"{label} 含未知欄位：{', '.join(unknown)}")
            file_value = _require_text(data, "file", label, errors)
            object_label = _require_text(data, "label", label, errors)
            evidence = _require_text(data, "evidence", label, errors)
            alt = _require_text(data, "alt", label, errors)
            guide = _require_text(data, "guide", label, errors)
            source = _require_text(data, "source", label, errors)

            pure = PurePosixPath(file_value) if file_value else PurePosixPath("__invalid__.png")
            safe_parts = (
                not pure.is_absolute()
                and len(pure.parts) >= 3
                and pure.parts[:2] == ("assets", "images")
                and all(part not in {"", ".", ".."} for part in pure.parts)
                and "\\" not in file_value
            )
            if not safe_parts:
                errors.append(f"{label} 的 `file` 必須是 assets/images/ 下的安全相對路徑")
            if pure.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                errors.append(f"{label} 的 `file` 必須是 PNG、JPG 或 JPEG")
            local_path = (paper_dir.joinpath(*pure.parts)).resolve()
            if not _is_within(local_path, paper_dir):
                errors.append(f"{label} 的 `file` 不可離開論文資料夾")
            _check_file(local_path, "圖片 attachment", errors)

            if object_label and not re.fullmatch(OBJECT_LABEL_PATTERN, object_label):
                errors.append(f"{label} 的 `label` 必須只含 Figure／Table／Algorithm 與原編號")
            if evidence and evidence not in {"作者主張", "實驗事實", "分析", "推測"}:
                errors.append(f"{label} 的 `evidence` 必須是作者主張、實驗事實、分析或推測")
            if guide.startswith("導讀：") or guide.startswith("導讀:"):
                errors.append(f"{label} 的 `guide` 不要自行加入「導讀：」前綴")
            if source and not PDF_SOURCE_RE.search(source):
                errors.append(f"{label} 的 `source` 必須包含 PDF p.N")
            source_objects = OBJECT_LABEL_RE.findall(source) if source else []
            if source and object_label not in source_objects:
                errors.append(f"{label} 的 `source` 必須包含與 `label` 完全相同的原物件編號")
            if source and not SOURCE_LOCATOR_RE.search(source):
                errors.append(f"{label} 的 `source` 必須包含原文章節或附錄定位")
            if alt and re.search(r"(?:裁切自|擷取自|上傳自|原論文圖片)", alt):
                errors.append(f"{label} 的 `alt` 應描述圖片，不應描述產製過程")

            width = data.get("width")
            if width is not None and (not isinstance(width, int) or isinstance(width, bool) or not 200 <= width <= 1600):
                errors.append(f"{label} 的 `width` 必須是 200–1600 的整數")
            attachment_name = pure.name

        directives.append(
            Directive(
                kind=kind,
                data=data,
                local_path=local_path,
                attachment_name=attachment_name,
                token=f"PAPERCONFLUENCEDIRECTIVE{index:04d}",
            )
        )

    return directives


def _analyze_markdown(text: str, markup: ModuleType) -> SemanticSummary:
    blocks = markup.parse_blocks(text.replace(TEMPLATE_MARKER, ""))
    headings: list[tuple[str, str]] = []
    content_counts: dict[int, int] = {index: 0 for index in range(1, 17)}
    prose_units: dict[int, list[str]] = {index: [] for index in range(1, 17)}
    table_rows: dict[int, list[list[str]]] = {index: [] for index in range(1, 17)}
    list_item_counts: dict[int, int] = {index: 0 for index in range(1, 17)}
    directive_sections: list[tuple[str, Optional[int]]] = []
    preface_units: list[str] = []
    code_units: list[str] = []
    claim_units: dict[int, list[str]] = {index: [] for index in range(1, 17)}
    h1_count = 0
    other_heading_count = 0
    current_section: Optional[int] = None

    def add_prose(value: str) -> None:
        cleaned = value.strip()
        if not cleaned:
            return
        if current_section is None:
            preface_units.append(cleaned)
        elif 1 <= current_section <= 16:
            prose_units[current_section].append(cleaned)

    def add_claim(value: str) -> None:
        cleaned = value.strip()
        if cleaned and current_section is not None and 1 <= current_section <= 16:
            claim_units[current_section].append(cleaned)

    for block in blocks:
        kind = block["type"]
        if kind == "heading":
            level = block["level"]
            if level == 1:
                h1_count += 1
            if level == 2:
                match = re.fullmatch(r"(\d{2})\.\s+(.+?)\s*", block["text"])
                if match:
                    number, title = match.groups()
                    headings.append((number, title))
                    current_section = int(number) if number.isdigit() else None
                else:
                    headings.append(("", block["text"].strip()))
                    current_section = None
            elif current_section is not None:
                other_heading_count += 1
                content_counts[current_section] += 1
                add_prose(block["text"])
            continue

        if current_section is not None and 1 <= current_section <= 16 and kind != "rule":
            content_counts[current_section] += 1

        if kind == "code":
            lang = (block.get("lang") or "").lower()
            if lang in {"paper-image", "paper-attachment"}:
                directive_sections.append((lang, current_section))
            else:
                code_units.append(str(block.get("text") or ""))
        elif kind in {"paragraph", "quote"}:
            add_prose(block.get("text") or "")
            add_claim(block.get("text") or "")
        elif kind == "list":
            items = block.get("items") or []
            if current_section is not None and 1 <= current_section <= 16:
                list_item_counts[current_section] += sum(
                    1 for item in items if int(item.get("level") or 0) == 0
                )
            for item in items:
                add_prose(item.get("text") or "")
                add_claim(item.get("text") or "")
        elif kind == "table":
            rows = [block.get("header") or [], *(block.get("rows") or [])]
            for row_index, row in enumerate(rows):
                if current_section is not None and 1 <= current_section <= 16:
                    table_rows[current_section].append([str(cell) for cell in row])
                add_prose(" | ".join(str(cell) for cell in row))
                if row_index:
                    add_claim(" | ".join(str(cell) for cell in row))

    return SemanticSummary(
        headings=headings,
        h1_count=h1_count,
        other_heading_count=other_heading_count,
        content_counts=content_counts,
        prose_units=prose_units,
        table_rows=table_rows,
        list_item_counts=list_item_counts,
        directive_sections=directive_sections,
        preface_units=preface_units,
        code_units=code_units,
        claim_units=claim_units,
    )


def validate_draft(
    text: str,
    source: Path,
    paper_dir: Path,
    project_root: Path,
    markup: ModuleType,
    allow_legacy_folder_title: bool = False,
) -> list[Directive]:
    errors: list[str] = []
    source = source.resolve()
    paper_dir = paper_dir.resolve()
    project_root = project_root.resolve()

    if source.name != "confluence-summary.md":
        errors.append("來源稿檔名必須是 confluence-summary.md")
    if source.parent != paper_dir:
        errors.append("confluence-summary.md 必須直接位於論文資料夾")
    if not _is_within(paper_dir, project_root):
        errors.append("論文資料夾必須位於 Paper Reading root 之下")
        relative = None
    else:
        relative = paper_dir.relative_to(project_root)
        if len(relative.parts) != 3:
            errors.append("論文資料夾必須符合 <Topic>/<Subtopic>/<Formal Paper Title> 三層結構")

    if text.count(TEMPLATE_MARKER) != 1:
        errors.append(f"來源稿必須恰有一個模板版本標記 `{TEMPLATE_MARKER}`")
    if XML_INVALID_RE.search(text):
        errors.append("來源稿含 XML 1.0 不允許的控制字元或 Unicode surrogate")

    placeholders = sorted(set(PLACEHOLDER_RE.findall(text)))
    if placeholders:
        preview = ", ".join(placeholders[:8])
        suffix = " ..." if len(placeholders) > 8 else ""
        errors.append(f"仍有未填 placeholder：{preview}{suffix}")
    if re.search(r"(?im)^\s*(?:TODO|TBD)(?:\s|:|$)", text):
        errors.append("來源稿仍含 TODO／TBD")
    if re.search(r"(?m)^\s*\|.*\\\|.*\|\s*$", text):
        errors.append("目前 Confluence converter 不支援 table cell 內的 escaped pipe；請改寫內容")

    semantic = _analyze_markdown(text, markup)
    prose_by_section = {
        section: "\n".join(units) for section, units in semantic.prose_units.items()
    }
    visible_prose = "\n".join([*semantic.preface_units, *prose_by_section.values()])
    non_code_visible_prose = "\n".join(
        _inline_plain(unit, markup, omit_code=True)
        for unit in [*semantic.preface_units, *(unit for units in semantic.prose_units.values() for unit in units)]
    )
    safety_text = "\n".join([visible_prose, *semantic.code_units])
    observed = [(number, title.strip()) for number, title in semantic.headings]
    expected = [(f"{index:02d}", title) for index, title in enumerate(EXPECTED_SECTIONS, 1)]
    if observed != expected:
        errors.append("16 個二級章節的編號、標題或順序不符合固定模板")
    if len(semantic.headings) != 16:
        errors.append(f"來源稿必須恰有 16 個二級標題，目前為 {len(semantic.headings)}")
    if semantic.h1_count:
        errors.append("Confluence page title 已充當 H1；來源稿 body 不可再放一級標題")
    if semantic.other_heading_count:
        errors.append("來源稿只允許模板的 16 個 H2；請用粗體段落或列表組織子主題")

    metadata_values: dict[str, str] = {}
    if semantic.headings == expected:
        for index in range(1, 17):
            if semantic.content_counts[index] == 0:
                errors.append(f"第 {index:02d} 章不得留空；缺資料時寫「論文未提供」")
        section_one = "\n".join(semantic.prose_units[1])
        metadata_rows = semantic.table_rows[1]
        observed_fields = [row[0].strip() for row in metadata_rows if row]
        if observed_fields != METADATA_FIELDS or any(len(row) != 2 for row in metadata_rows):
            errors.append("第 01 章 metadata table 必須恰有固定的兩欄欄位與順序")
        metadata_values = {
            row[0].strip(): row[1].strip()
            for row in metadata_rows
            if len(row) == 2
        }
        for field in METADATA_FIELDS[1:]:
            if not metadata_values.get(field, "").strip():
                errors.append(f"第 01 章 metadata 的「{field}」不可為空")
        year = metadata_values.get("年份", "")
        if year and not re.fullmatch(r"(?:19|20)\d{2}", year):
            errors.append("第 01 章 metadata 的「年份」必須是四位西元年")
        updated = metadata_values.get("最後更新", "")
        if updated:
            try:
                parsed_updated = date.fromisoformat(updated)
            except ValueError:
                errors.append("第 01 章 metadata 的「最後更新」必須是有效 YYYY-MM-DD 日期")
            else:
                if parsed_updated.isoformat() != updated:
                    errors.append("第 01 章 metadata 的「最後更新」必須是有效 YYYY-MM-DD 日期")
                elif parsed_updated > date.today():
                    errors.append("第 01 章 metadata 的「最後更新」不可晚於今天")
        page_value = metadata_values.get("頁數", "")
        if page_value and not re.fullmatch(r"共\s*[1-9]\d*\s*頁", page_value):
            errors.append("第 01 章 metadata 的「頁數」必須恰為「共 N 頁」")
        if relative is not None and len(relative.parts) == 3:
            expected_classification = f"{relative.parts[0]} / {relative.parts[1]}"
            if metadata_values.get("分類") != expected_classification:
                errors.append(
                    "第 01 章 metadata 的「分類」必須精確對應實體資料夾："
                    + expected_classification
                )
            formal_title = metadata_values.get("正式標題", "")
            if (
                formal_title
                and not _folder_matches_formal_title(formal_title, relative.parts[2])
                and not allow_legacy_folder_title
            ):
                errors.append("第 01 章 metadata 的「正式標題」未對應論文資料夾名稱")
        classification_reason = metadata_values.get("分類理由", "")
        if classification_reason and not classification_reason.startswith("**[分析]**"):
            errors.append("第 01 章 metadata 的「分類理由」必須以 **[分析]** 開頭")
        if classification_reason and not (
            PDF_SOURCE_RE.search(classification_reason)
            and SOURCE_LOCATOR_RE.search(classification_reason)
        ):
            errors.append("第 01 章 metadata 的「分類理由」必須含原文章節與 PDF p.N 來源")
        canonical_links = [
            match.group(1)
            for unit in semantic.prose_units[1]
            if (
                match := re.fullmatch(
                    r"\[論文頁面\]\((https://[^\s()]+)\)", unit.strip()
                )
            )
        ]
        if len(canonical_links) != 1:
            errors.append(
                "第 01 章必須恰有一行 `[論文頁面](canonical HTTPS URL)`；"
                "URL 的括號需 percent-encode"
            )
        question_count = semantic.list_item_counts[15]
        if not 3 <= question_count <= 5:
            errors.append(f"第 15 章必須有 3–5 個列表問題，目前為 {question_count}")

        priority_text = "\n".join(semantic.preface_units)
        priority_numbers = {
            int(number)
            for number in re.findall(r"(?<!\d)(0?[1-9]|1[0-6])(?!\d)", priority_text)
        }
        if "**優先閱讀：**" not in priority_text or len(priority_numbers) != 3:
            errors.append("頁首必須保留「優先閱讀」，並列出恰好三個有效章節編號")

        for index in range(2, 15):
            body = "\n".join(semantic.prose_units[index])
            if index == 8:
                has_image = any(
                    kind == "paper-image" and section == 8
                    for kind, section in semantic.directive_sections
                )
                has_reasoned_no_image = any(
                    re.search(
                        rf"{re.escape(NO_IMAGE_MARKER)}\s*(?![（(]*來源\s*[:：])[^。\n]{{2,}}",
                        statement,
                    )
                    for unit in semantic.claim_units[8]
                    for statement in SENTENCE_SPLIT_RE.split(unit)
                )
                has_explicit_absence = any(
                    statement.strip().rstrip("。. ") == NO_IMAGE_ABSENCE_MARKER
                    for unit in semantic.claim_units[8]
                    for statement in SENTENCE_SPLIT_RE.split(unit)
                )
                has_empty_marker = any(
                    _is_not_provided_only(statement)
                    for unit in semantic.claim_units[8]
                    for statement in SENTENCE_SPLIT_RE.split(unit)
                )
                if not has_image and not (
                    has_reasoned_no_image or has_explicit_absence or has_empty_marker
                ):
                    errors.append(
                        "第 08 章必須包含 paper-image block、單獨寫「論文未提供」，"
                        f"或以「{NO_IMAGE_MARKER}<具體理由>」說明無需擷取"
                    )
                continue
            has_empty_marker = any(
                _is_not_provided_only(statement)
                for unit in semantic.claim_units[index]
                for statement in SENTENCE_SPLIT_RE.split(unit)
            )
            if not EVIDENCE_LABEL_RE.search(body) and not has_empty_marker:
                errors.append(f"第 {index:02d} 章至少要有一個 evidence label，或明確寫「論文未提供」")

        for section in range(2, 15):
            for unit in semantic.claim_units[section]:
                for statement in filter(
                    None, (part.strip() for part in SENTENCE_SPLIT_RE.split(unit))
                ):
                    if _is_not_provided_only(statement) or _is_source_only(statement):
                        continue
                    if not EVIDENCE_LABEL_RE.search(statement):
                        kind = "數值" if _contains_material_number(statement) else "定性"
                        errors.append(
                            f"第 {section:02d} 章含未在同一句標示 evidence label 的{kind}主張："
                            + statement[:80]
                        )

        section_sixteen = prose_by_section[16]
        section_sixteen_empty = any(
            _is_not_provided_only(statement)
            for unit in semantic.claim_units[16]
            for statement in SENTENCE_SPLIT_RE.split(unit)
        )
        if not section_sixteen_empty and not (
            PDF_SOURCE_RE.search(section_sixteen) and SOURCE_LOCATOR_RE.search(section_sixteen)
        ):
            errors.append("第 16 章重點索引至少要有一組原文章節與 PDF p.N 定位，或寫「論文未提供」")
        for unit in semantic.claim_units[16]:
            for statement in filter(
                None, (part.strip() for part in SENTENCE_SPLIT_RE.split(unit))
            ):
                if (
                    _is_not_provided_only(statement)
                    or _is_source_only(statement)
                    or statement in {"**術語**", "**重點索引**"}
                ):
                    continue
                if not EVIDENCE_LABEL_RE.search(statement):
                    errors.append(
                        "第 16 章每個術語或重點索引項目必須在同一句使用 evidence label："
                        + statement[:80]
                    )
                if not (PDF_SOURCE_RE.search(unit) and SOURCE_LOCATOR_RE.search(unit)):
                    errors.append(
                        "第 16 章每個術語或重點索引項目必須在同一列表項／段落含原文章節與 PDF p.N："
                        + statement[:80]
                    )

        for section, units in semantic.prose_units.items():
            for unit_index, unit in enumerate(units):
                bare_labels = re.findall(r"\[(作者主張|實驗事實|分析|推測)\]", unit)
                strong_labels = EVIDENCE_LABEL_RE.findall(unit)
                if bare_labels and len(bare_labels) != len(strong_labels):
                    errors.append(f"第 {section:02d} 章的 evidence label 必須使用粗體固定格式")
                if not strong_labels:
                    continue
                window_parts = [unit]
                for following in units[unit_index + 1 : unit_index + 3]:
                    if EVIDENCE_LABEL_RE.search(following):
                        break
                    window_parts.append(following)
                window = "\n".join(window_parts)
                if not PDF_SOURCE_RE.search(window):
                    errors.append(f"第 {section:02d} 章的 evidence label 附近缺少 PDF p.N 來源")
                if not SOURCE_LOCATOR_RE.search(window):
                    errors.append(f"第 {section:02d} 章的 evidence label 附近缺少原文章節或附錄定位")

    page_counts = PAGE_COUNT_RE.findall("\n".join(prose_by_section.values()))
    if len(page_counts) != 1:
        errors.append(f"可見內容必須恰有一個 `共 N 頁`，目前為 {len(page_counts)}")
    if PAGE_COUNT_RE.search(prose_by_section[1]) is None and page_counts:
        errors.append("`共 N 頁` 必須位於第 01 章")
    if MARKDOWN_IMAGE_RE.search(visible_prose):
        errors.append("不可使用 Markdown image；請改用 paper-image fenced JSON block")
    if RAW_HTML_RE.search(non_code_visible_prose):
        errors.append("來源稿不可手寫 HTML 或 Confluence storage tags")
    unsafe_links = sorted(
        {
            str(span.get("href") or "")
            for unit in [
                *semantic.preface_units,
                *(item for units in semantic.prose_units.values() for item in units),
            ]
            for span in markup.parse_inline(unit)
            if "link" in span.get("marks", [])
            and not str(span.get("href") or "").startswith(("https://", "#"))
        }
    )
    if unsafe_links:
        errors.append(
            "一般 Markdown link 只能使用 HTTPS 或頁內 anchor；PDF／圖片必須走 attachment block："
            + ", ".join(unsafe_links[:4])
        )
    if NESTED_PAREN_LINK_RE.search(visible_prose):
        errors.append("目前 converter 不支援 Markdown link destination 的 raw parentheses；請 percent-encode")
    inline_code_text = "\n".join(
        str(span.get("text") or "")
        for unit in [
            *semantic.preface_units,
            *(item for units in semantic.prose_units.values() for item in units),
        ]
        for span in markup.parse_inline(unit)
        if "code" in span.get("marks", [])
    )
    code_visible_text = "\n".join([*semantic.code_units, inline_code_text])
    if (
        "file://" in safety_text.lower()
        or WINDOWS_PATH_RE.search(safety_text)
        or _contains_posix_path(non_code_visible_prose)
        or _contains_posix_path(code_visible_text, allow_api_endpoint=True)
    ):
        errors.append("讀者可見來源稿不可包含 file:// 或本機絕對路徑")

    for name, pattern in FORBIDDEN_VISIBLE_PATTERNS.items():
        if pattern.search(safety_text):
            errors.append(f"讀者可見內容含禁止的作業資訊：{name}")

    evidence_labels = set(
        EVIDENCE_LABEL_RE.findall(visible_prose)
    )
    if not evidence_labels:
        errors.append("來源稿至少要使用一種可見 evidence label")

    directives = _parse_directives(text, paper_dir, errors)
    directive_visible_text = "\n".join(
        str(item.data.get(field) or "")
        for item in directives
        for field in ("label", "evidence", "description", "alt", "guide", "source")
    )
    if RAW_HTML_RE.search(directive_visible_text):
        errors.append("attachment 的讀者可見欄位不可含 HTML 或 storage tags")
    if (
        "file://" in directive_visible_text.lower()
        or WINDOWS_PATH_RE.search(directive_visible_text)
        or _contains_posix_path(directive_visible_text)
    ):
        errors.append("attachment 的讀者可見欄位不可含 file:// 或本機絕對路徑")
    for name, pattern in FORBIDDEN_VISIBLE_PATTERNS.items():
        if pattern.search(directive_visible_text):
            errors.append(f"attachment 的讀者可見欄位含禁止的作業資訊：{name}")
    pdf_directives = [item for item in directives if item.kind == "paper-attachment"]
    if len(pdf_directives) != 1:
        errors.append(f"來源稿必須恰有一個 paper-attachment PDF block，目前為 {len(pdf_directives)}")
    elif pdf_directives[0].local_path.is_file() and PAGE_COUNT_RE.fullmatch(
        metadata_values.get("頁數", "")
    ):
        expected_pages = int(re.search(r"\d+", metadata_values["頁數"]).group())
        try:
            actual_pages = _pdf_page_count(pdf_directives[0].local_path)
        except DraftError as exc:
            errors.append(str(exc))
        else:
            if actual_pages != expected_pages:
                errors.append(
                    f"第 01 章頁數為 {expected_pages}，但 PDF 實際為 {actual_pages} 頁"
                )
    if len(semantic.directive_sections) != len(directives):
        errors.append("paper attachment directive 必須是頂層 fenced block，不可藏在其他 code fence")
    for item, (semantic_kind, section) in zip(directives, semantic.directive_sections):
        expected_section = 1 if item.kind == "paper-attachment" else 8
        if semantic_kind != item.kind or section != expected_section:
            errors.append(
                f"{item.kind} `{item.attachment_name}` 必須位於第 {expected_section:02d} 章，目前位於 {section or '章節之外'}"
            )

    attachment_names = [item.attachment_name.casefold() for item in directives]
    duplicates = sorted({name for name in attachment_names if attachment_names.count(name) > 1})
    if duplicates:
        errors.append(f"attachment filename 不得重複引用：{', '.join(duplicates)}")

    if errors:
        raise DraftError("\n".join(f"- {message}" for message in errors))
    return directives


def _load_atlassian_markup(atlassian_cli: Path) -> ModuleType:
    atlassian_cli = atlassian_cli.resolve()
    if not atlassian_cli.is_file() or atlassian_cli.name != "atlassian.py":
        raise DraftError(f"找不到有效的 slai-atlassian CLI：{atlassian_cli}")
    markup_path = atlassian_cli.with_name("markup.py")
    if not markup_path.is_file():
        raise DraftError(f"找不到 CLI 的 Markdown converter：{markup_path}")

    spec = importlib.util.spec_from_file_location("paper_reading_atlassian_markup", markup_path)
    if spec is None or spec.loader is None:
        raise DraftError(f"無法載入 Markdown converter：{markup_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "md_to_storage", None)):
        raise DraftError("slai-atlassian markup.py 未提供 md_to_storage()")
    return module


def _cdata(text: str) -> str:
    return text.replace("]]>", "]]]]><![CDATA[>")


def _render_directive(item: Directive) -> str:
    data = item.data
    filename = html.escape(item.attachment_name, quote=True)
    if item.kind == "paper-attachment":
        label = _cdata(str(data["label"]).strip())
        description = str(data.get("description") or "").strip()
        suffix = f" — {html.escape(description, quote=False)}" if description else ""
        return (
            "<p><ac:link>"
            f'<ri:attachment ri:filename="{filename}"/>'
            f"<ac:plain-text-link-body><![CDATA[{label}]]></ac:plain-text-link-body>"
            f"</ac:link>{suffix}</p>"
        )

    object_label = html.escape(str(data["label"]).strip(), quote=False)
    evidence = html.escape(str(data["evidence"]).strip(), quote=False)
    alt = html.escape(str(data["alt"]).strip(), quote=True)
    guide = html.escape(str(data["guide"]).strip(), quote=False)
    source = html.escape(str(data["source"]).strip(), quote=False)
    width = data.get("width")
    width_attr = f' ac:width="{width}"' if width is not None else ""
    return (
        f'<p><ac:image ac:alt="{alt}"{width_attr}>'
        f'<ri:attachment ri:filename="{filename}"/>'
        "</ac:image></p>"
        f"<p><strong>{object_label}</strong><br/>"
        f"<strong>[{evidence}]</strong> "
        f"<strong>導讀：</strong>{guide}<br/>"
        f"<em>來源：{source}</em></p>"
    )


def _parse_storage(storage: str) -> ET.Element:
    try:
        return ET.fromstring(
            '<root xmlns:ac="urn:confluence-ac" xmlns:ri="urn:confluence-ri">'
            + storage
            + "</root>"
        )
    except (ET.ParseError, UnicodeError) as exc:
        raise DraftError(f"產出的 storage XHTML 無法解析：{exc}") from exc


def _storage_text_without_code(element: ET.Element, ac: str) -> str:
    pieces: list[str] = []

    def visit(node: ET.Element) -> None:
        is_code = (
            node.tag == f"{ac}structured-macro"
            and node.attrib.get(f"{ac}name") == "code"
        )
        if is_code:
            return
        if node.text:
            pieces.append(node.text)
        for child in node:
            visit(child)
            if child.tail:
                pieces.append(child.tail)

    visit(element)
    return "".join(pieces)


def _validate_storage_structure(
    storage: str,
    directives: list[Directive],
    source_text: str,
    markup: ModuleType,
) -> None:
    root = _parse_storage(storage)
    ac = "{urn:confluence-ac}"
    ri = "{urn:confluence-ri}"
    errors: list[str] = []
    top_level = list(root)

    headings = ["".join(element.itertext()).strip() for element in root.iter("h2")]
    expected_headings = [
        f"{index:02d}. {title}" for index, title in enumerate(EXPECTED_SECTIONS, 1)
    ]
    if headings != expected_headings:
        errors.append("storage XHTML 的 16 個 H2 與固定章節不一致")
    if any(True for _ in root.iter("h1")):
        errors.append("storage XHTML 不可含 H1")

    toc_count = sum(
        1
        for element in root.iter(f"{ac}structured-macro")
        if element.attrib.get(f"{ac}name") == "toc"
    )
    if toc_count != 1:
        errors.append(f"storage XHTML 必須恰有一個 TOC macro，目前為 {toc_count}")

    attachment_refs = [
        element.attrib.get(f"{ri}filename", "")
        for element in root.iter(f"{ri}attachment")
    ]
    expected_refs = [item.attachment_name for item in directives]
    if sorted(attachment_refs) != sorted(expected_refs):
        errors.append("storage XHTML 的 attachment references 與來源稿 directives 不一致")

    image_count = sum(1 for _ in root.iter(f"{ac}image"))
    expected_images = sum(1 for item in directives if item.kind == "paper-image")
    if image_count != expected_images:
        errors.append(f"storage XHTML 圖片數量不符：預期 {expected_images}，實際 {image_count}")

    source_blocks = markup.parse_blocks(source_text.replace(TEMPLATE_MARKER, ""))
    expected_tables: list[list[list[str]]] = []
    expected_code: list[tuple[str, str]] = []
    for block in source_blocks:
        if block["type"] == "table":
            rows = [block.get("header") or [], *(block.get("rows") or [])]
            expected_tables.append(
                [[_inline_plain(str(cell), markup) for cell in row] for row in rows]
            )
        elif block["type"] == "code" and (block.get("lang") or "").lower() not in {
            "paper-image",
            "paper-attachment",
        }:
            expected_code.append(((block.get("lang") or ""), str(block.get("text") or "")))

    actual_tables: list[list[list[str]]] = []
    for table in root.iter("table"):
        rows: list[list[str]] = []
        for row in table.iter("tr"):
            cells = [
                "".join(cell.itertext()).strip()
                for cell in row
                if cell.tag in {"th", "td"}
            ]
            rows.append(cells)
        actual_tables.append(rows)
    if actual_tables != expected_tables:
        errors.append("storage XHTML 的表格欄位或內容未與來源稿等價保留")

    actual_code: list[tuple[str, str]] = []
    for macro in root.iter(f"{ac}structured-macro"):
        if macro.attrib.get(f"{ac}name") != "code":
            continue
        language = ""
        for parameter in macro.iter(f"{ac}parameter"):
            if parameter.attrib.get(f"{ac}name") == "language":
                language = "".join(parameter.itertext())
                break
        body = next(iter(macro.iter(f"{ac}plain-text-body")), None)
        actual_code.append((language, "" if body is None else "".join(body.itertext())))
    if actual_code != expected_code:
        errors.append("storage XHTML 的公式／code block 未與來源稿等價保留")

    source_semantic = _analyze_markdown(source_text, markup)
    source_prose = "\n".join(
        [
            *source_semantic.preface_units,
            *(unit for units in source_semantic.prose_units.values() for unit in units),
        ]
    )
    directive_text = "\n".join(
        str(item.data.get(field) or "")
        for item in directives
        for field in ("label", "evidence", "description", "alt", "guide", "source")
    )
    storage_plain = _storage_text_without_code(root, ac)

    directive_iter = iter(directives)

    def contract_token(_match: re.Match[str]) -> str:
        return "\n" + next(directive_iter).token + "\n"

    contract_source = DIRECTIVE_RE.sub(contract_token, source_text).replace(
        TEMPLATE_MARKER, ""
    )
    directive_by_token = {item.token: item for item in directives}
    expected_reader_parts: list[str] = []
    expected_structure: list[str] = []
    expected_links: list[tuple[str, str]] = []

    def add_inline_links(value: str) -> None:
        active_href: Optional[str] = None
        active_text: list[str] = []

        def flush() -> None:
            nonlocal active_href, active_text
            if active_href is not None:
                expected_links.append(("".join(active_text), active_href))
            active_href = None
            active_text = []

        for span in markup.parse_inline(value):
            marks = span.get("marks", [])
            href = str(span.get("href") or "") if "link" in marks else None
            if href is None:
                flush()
            elif active_href == href:
                active_text.append(str(span.get("text") or ""))
            else:
                flush()
                active_href = href
                active_text.append(str(span.get("text") or ""))
        flush()

    for block in markup.parse_blocks(contract_source):
        kind = block["type"]
        if kind in {"paragraph", "heading", "quote"}:
            block_text = str(block.get("text") or "")
            item = directive_by_token.get(block_text.strip())
            if kind == "heading":
                expected_structure.append(f"h{int(block['level'])}")
            elif kind == "quote":
                expected_structure.append("blockquote")
            elif item is not None and item.kind == "paper-image":
                expected_structure.extend(["p", "p"])
            else:
                expected_structure.append("p")
            if item is None:
                add_inline_links(block_text)
                expected_reader_parts.append(_inline_plain(block_text, markup))
            elif item.kind == "paper-attachment":
                attachment_text = str(item.data["label"]).strip()
                description = str(item.data.get("description") or "").strip()
                if description:
                    attachment_text += " — " + description
                expected_reader_parts.append(attachment_text)
            else:
                expected_reader_parts.append(
                    f"{str(item.data['label']).strip()}"
                    f"[{str(item.data['evidence']).strip()}] "
                    f"導讀：{str(item.data['guide']).strip()}"
                    f"來源：{str(item.data['source']).strip()}"
                )
        elif kind == "list":
            expected_structure.append("ol" if block.get("ordered") else "ul")
            for list_item in block.get("items") or []:
                add_inline_links(str(list_item.get("text") or ""))
            expected_reader_parts.append(
                "".join(
                    _inline_plain(str(item.get("text") or ""), markup)
                    for item in (block.get("items") or [])
                )
            )
        elif kind == "table":
            expected_structure.append("table")
            rows = [block.get("header") or [], *(block.get("rows") or [])]
            for row in rows:
                for cell in row:
                    add_inline_links(str(cell))
            expected_reader_parts.append(
                "".join(
                    _inline_plain(str(cell), markup) for row in rows for cell in row
                )
            )
        elif kind == "rule":
            expected_structure.append("hr")
        elif kind == "code":
            expected_structure.append("code")

    actual_structure: list[str] = []
    actual_reader_parts: list[str] = []
    for node in top_level:
        if node.tag == f"{ac}structured-macro":
            macro_name = node.attrib.get(f"{ac}name")
            if macro_name == "toc":
                continue
            actual_structure.append("code" if macro_name == "code" else f"macro:{macro_name}")
        else:
            actual_structure.append(str(node.tag))
            node_text = "".join(node.itertext())
            if node_text.strip():
                actual_reader_parts.append(node_text)
    if actual_structure != expected_structure:
        errors.append("storage XHTML 的段落、列表、引言、表格或 code block 結構不一致")

    actual_links = [
        ("".join(element.itertext()), element.attrib.get("href", ""))
        for element in root.iter("a")
    ]
    if actual_links != expected_links:
        errors.append("storage XHTML 的一般連結文字或 destination 與來源稿不一致")

    def normalize_reader_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    if [normalize_reader_text(value) for value in actual_reader_parts] != [
        normalize_reader_text(value) for value in expected_reader_parts
    ]:
        errors.append("storage XHTML 的一般正文、清單、引言或次級標題未與來源稿等價保留")

    for label in ("作者主張", "實驗事實", "分析", "推測"):
        expected_count = len(re.findall(rf"\*\*\[{label}\]\*\*", source_prose)) + sum(
            1
            for item in directives
            if item.kind == "paper-image" and item.data.get("evidence") == label
        )
        actual_count = sum(
            1
            for element in root.iter("strong")
            if "".join(element.itertext()).strip() == f"[{label}]"
        )
        if actual_count != expected_count:
            errors.append(f"storage XHTML 的 [{label}] evidence label 數量不符")
    expected_pdf_sources = len(PDF_SOURCE_RE.findall(source_prose + "\n" + directive_text))
    if len(PDF_SOURCE_RE.findall(storage_plain)) != expected_pdf_sources:
        errors.append("storage XHTML 的 PDF p.N 來源標記數量不符")

    section_one = "\n".join(source_semantic.prose_units[1])
    expected_urls = [
        match.group(1)
        for unit in source_semantic.prose_units[1]
        if (
            match := re.fullmatch(
                r"\[論文頁面\]\((https://[^\s()]+)\)", unit.strip()
            )
        )
    ]
    actual_urls = [
        element.attrib.get("href", "")
        for element in root.iter("a")
        if "".join(element.itertext()).strip() == "論文頁面"
    ]
    if actual_urls != expected_urls:
        errors.append("storage XHTML 的 canonical 論文連結與來源稿不一致")

    for item in directives:
        if item.kind == "paper-attachment":
            matching_paragraphs = [
                node
                for node in top_level
                if node.tag == "p"
                and any(
                    attachment.attrib.get(f"{ri}filename") == item.attachment_name
                    for attachment in node.iter(f"{ri}attachment")
                )
                and any(True for _ in node.iter(f"{ac}link"))
            ]
            expected_text = str(item.data["label"]).strip()
            description = str(item.data.get("description") or "").strip()
            if description:
                expected_text += " — " + description
            if len(matching_paragraphs) != 1 or "".join(
                matching_paragraphs[0].itertext()
            ).strip() != expected_text:
                errors.append("storage XHTML 的 PDF attachment 連結文字或說明不一致")
            continue

        matching_positions: list[tuple[int, ET.Element]] = []
        for position, node in enumerate(top_level):
            for image in node.iter(f"{ac}image"):
                if any(
                    attachment.attrib.get(f"{ri}filename") == item.attachment_name
                    for attachment in image.iter(f"{ri}attachment")
                ):
                    matching_positions.append((position, image))
        if len(matching_positions) != 1:
            errors.append(f"storage XHTML 找不到唯一圖片節點：{item.attachment_name}")
            continue
        position, image = matching_positions[0]
        if image.attrib.get(f"{ac}alt") != str(item.data["alt"]).strip():
            errors.append(f"storage XHTML 圖片 alt 不一致：{item.attachment_name}")
        expected_width = item.data.get("width")
        actual_width = image.attrib.get(f"{ac}width")
        if actual_width != (str(expected_width) if expected_width is not None else None):
            errors.append(f"storage XHTML 圖片 width 不一致：{item.attachment_name}")
        caption = top_level[position + 1] if position + 1 < len(top_level) else None
        caption_text = "" if caption is None else "".join(caption.itertext()).strip()
        expected_caption = (
            f"{str(item.data['label']).strip()}"
            f"[{str(item.data['evidence']).strip()}] "
            f"導讀：{str(item.data['guide']).strip()}"
            f"來源：{str(item.data['source']).strip()}"
        )
        if caption is None or caption.tag != "p" or caption_text != expected_caption:
            errors.append(f"storage XHTML 圖說內容不一致：{item.attachment_name}")

    if errors:
        raise DraftError("\n".join(f"- {message}" for message in errors))


def render_storage(text: str, directives: Iterable[Directive], markup: ModuleType) -> str:
    directive_list = list(directives)
    by_index = iter(directive_list)

    def replace_block(match: re.Match[str]) -> str:
        item = next(by_index)
        return f"\n\n{item.token}\n\n"

    prepared = DIRECTIVE_RE.sub(replace_block, text)
    prepared = prepared.replace(TEMPLATE_MARKER, "")
    storage = markup.md_to_storage(prepared)

    for item in directive_list:
        token_paragraph = f"<p>{item.token}</p>"
        if token_paragraph not in storage:
            raise DraftError(f"轉換器未保留 attachment token：{item.token}")
        storage = storage.replace(token_paragraph, _render_directive(item), 1)

    if "PAPERCONFLUENCEDIRECTIVE" in storage or PLACEHOLDER_RE.search(storage):
        raise DraftError("產出的 storage XHTML 仍含內部 token 或 placeholder")

    toc = '<ac:structured-macro ac:name="toc" ac:schema-version="1"/>'
    storage = STORAGE_GENERATOR_MARKER + toc + storage
    _validate_storage_structure(storage, directive_list, text, markup)
    return storage


def _validate_output_target(
    output: Path,
    source: Path,
    directives: Iterable[Directive],
    overwrite_output: bool,
) -> Path:
    resolved = output.resolve()
    if not resolved.name.lower().endswith(".storage.xhtml"):
        raise DraftError("--output 檔名必須以 .storage.xhtml 結尾")
    protected_paths = {
        source.resolve(),
        *(item.local_path.resolve() for item in directives),
    }
    if resolved in protected_paths:
        raise DraftError("--output 不可指向 confluence-summary.md、PDF 或圖片附件")
    if resolved.exists() and resolved.is_dir():
        raise DraftError(f"--output 指向資料夾：{resolved}")
    if resolved.exists() and not overwrite_output:
        raise DraftError("--output 已存在；請使用新的暫存路徑，或確認後加 --overwrite-output")
    if resolved.exists() and overwrite_output:
        try:
            existing_prefix = resolved.read_text(encoding="utf-8-sig")[:512]
        except (OSError, UnicodeError) as exc:
            raise DraftError(f"無法確認既有 output 的來源：{exc}") from exc
        if not existing_prefix.startswith(STORAGE_GENERATOR_MARKER):
            raise DraftError(
                "--overwrite-output 只能覆寫含 paper-reading-confluence generator marker 的既有產物"
            )
    return resolved


def prepare(
    source: Path,
    paper_dir: Path,
    project_root: Path,
    atlassian_cli: Path,
    output: Path,
    overwrite_output: bool = False,
    allow_unreferenced_images: bool = False,
    allow_legacy_folder_title: bool = False,
) -> dict[str, Any]:
    if not source.is_file():
        raise DraftError(f"找不到來源稿：{source}")
    try:
        text = source.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise DraftError(f"無法以 UTF-8 讀取來源稿：{exc}") from exc
    markup = _load_atlassian_markup(atlassian_cli)
    directives = validate_draft(
        text,
        source,
        paper_dir,
        project_root,
        markup,
        allow_legacy_folder_title=allow_legacy_folder_title,
    )

    image_dir = paper_dir.resolve() / "assets" / "images"
    existing_images = (
        sorted(
            path.resolve()
            for path in image_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
        )
        if image_dir.is_dir()
        else []
    )
    referenced_images = {
        item.local_path.resolve() for item in directives if item.kind == "paper-image"
    }
    unreferenced_images = [path for path in existing_images if path not in referenced_images]
    if unreferenced_images and not allow_unreferenced_images:
        names = ", ".join(path.name for path in unreferenced_images[:8])
        suffix = " ..." if len(unreferenced_images) > 8 else ""
        raise DraftError(
            "assets/images 含未被 paper-image 引用的圖片："
            + names
            + suffix
            + "。確認它們不屬於摘要後才可使用 --allow-unreferenced-images。"
        )

    storage = render_storage(text, directives, markup)

    output = _validate_output_target(output, source, directives, overwrite_output)

    temporary_path: Optional[Path] = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=str(output.parent),
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(storage)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary_path), str(output))
        temporary_path = None
    except OSError as exc:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass
        raise DraftError(f"無法安全寫入 storage XHTML：{exc}") from exc

    return {
        "ok": True,
        "source": str(source.resolve()),
        "storage": str(output),
        "sections": len(EXPECTED_SECTIONS),
        "attachments": [
            {
                "kind": item.kind,
                "filename": item.attachment_name,
                "path": str(item.local_path),
                "bytes": item.local_path.stat().st_size,
                "sha256": _sha256(item.local_path),
            }
            for item in directives
        ],
        "unreferenced_images": [str(path) for path in unreferenced_images],
    }


def _sample_markdown(pdf_name: str) -> str:
    bodies: list[str] = []
    for index, title in enumerate(EXPECTED_SECTIONS, 1):
        if index == 1:
            body = (
                "| 欄位 | 內容 |\n| --- | --- |\n"
                "| 正式標題 | Formal Paper Title |\n| 作者 | 測試作者 |\n"
                "| 出處／版本 | 測試會議 |\n| 年份 | 2026 |\n"
                "| 分類 | Topic / Subtopic |\n"
                "| 分類理由 | **[分析]** 測試分類理由（來源：Abstract · PDF p.1） |\n"
                "| 頁數 | 共 1 頁 |\n| 最後更新 | 2026-09-08 |\n\n"
                "[論文頁面](https://example.com/paper?a=1&b=2)\n\n"
                "```paper-attachment\n"
                + json.dumps({"file": pdf_name, "label": "開啟論文 PDF"}, ensure_ascii=False)
                + "\n```"
            )
        elif index == 2:
            body = "**[作者主張]** 測試摘要。（來源：§1 · PDF p.1）"
        elif index == 7:
            body = "**[分析]** 測試公式：\n\n```text\nT = max(a, b)\n```\n\n（來源：§1 · PDF p.1）"
        elif index == 8:
            body = (
                "```paper-image\n"
                + json.dumps(
                    {
                        "file": "assets/images/fig-01-p01-overview.png",
                        "label": "Figure 1",
                        "evidence": "分析",
                        "alt": "測試架構圖 A & B",
                        "guide": "由左至右閱讀 A & B，並比較 C < D 與 E > F。",
                        "source": "§1 · PDF p.1 · Figure 1",
                        "width": 800,
                    },
                    ensure_ascii=False,
                )
                + "\n```"
            )
        elif index == 15:
            body = "- 問題一？\n- 問題二？\n- 問題三？"
        else:
            body = "**[分析]** 測試內容。（來源：§1 · PDF p.1）"
        bodies.append(f"## {index:02d}. {title}\n\n{body}")
    return TEMPLATE_MARKER + "\n\n> **優先閱讀：** 第 06、10、12 章\n\n---\n\n" + "\n\n".join(bodies) + "\n"


def run_self_test(atlassian_cli: Path) -> None:
    root = (Path.cwd() / "paper-reading-confluence-selftest-root").resolve()
    paper_dir = root / "Topic" / "Subtopic" / "Formal Paper Title"
    source = paper_dir / "confluence-summary.md"
    draft = _sample_markdown("Formal Paper Title.pdf")
    markup = _load_atlassian_markup(atlassian_cli)

    def validate_without_disk(
        candidate: str, *, allow_legacy_folder_title: bool = False
    ) -> list[Directive]:
        with mock.patch.object(sys.modules[__name__], "_check_file"):
            return validate_draft(
                candidate,
                source,
                paper_dir,
                root,
                markup,
                allow_legacy_folder_title=allow_legacy_folder_title,
            )

    directives = validate_without_disk(draft)
    storage = render_storage(draft, directives, markup)
    if len(directives) != 2 or not storage.startswith(STORAGE_GENERATOR_MARKER):
        raise DraftError("self-test happy path 不符合預期")
    try:
        _validate_storage_structure(
            storage.replace("測試摘要", "", 1), directives, draft, markup
        )
    except DraftError:
        pass
    else:
        raise DraftError("self-test prose corruption unexpectedly passed")
    flattened_quote = storage.replace("<blockquote>", "<p>", 1).replace(
        "</blockquote>", "</p>", 1
    )
    try:
        _validate_storage_structure(flattened_quote, directives, draft, markup)
    except DraftError:
        pass
    else:
        raise DraftError("self-test block structure corruption unexpectedly passed")

    spacing_draft = draft.replace("測試摘要", "therapist", 1)
    spacing_directives = validate_without_disk(spacing_draft)
    spacing_storage = render_storage(spacing_draft, spacing_directives, markup)
    try:
        _validate_storage_structure(
            spacing_storage.replace("therapist", "the rapist", 1),
            spacing_directives,
            spacing_draft,
            markup,
        )
    except DraftError:
        pass
    else:
        raise DraftError("self-test whitespace semantic corruption unexpectedly passed")

    linked_draft = draft.replace(
        "**[作者主張]** 測試摘要。",
        "**[作者主張]** [補充](https://example.org/a) 測試摘要。",
        1,
    )
    linked_directives = validate_without_disk(linked_draft)
    linked_storage = render_storage(linked_draft, linked_directives, markup)
    try:
        _validate_storage_structure(
            linked_storage.replace(
                'href="https://example.org/a"',
                'href="https://attacker.example/b"',
                1,
            ),
            linked_directives,
            linked_draft,
            markup,
        )
    except DraftError:
        pass
    else:
        raise DraftError("self-test link destination corruption unexpectedly passed")

    if _folder_matches_formal_title("It's Time", "Its Time"):
        raise DraftError("self-test safe title punctuation loss unexpectedly passed")
    if not _folder_matches_formal_title("Title: Subtitle", "Title - Subtitle"):
        raise DraftError("self-test Windows-unsafe title substitution unexpectedly failed")

    legitimate_validation_claim = draft.replace(
        "**[分析]** 測試內容。（來源：§1 · PDF p.1）",
        "**[分析]** 形式驗證成功率為 95%。（來源：§1 · PDF p.1）",
        1,
    ).replace(
        "**[作者主張]** 測試摘要。",
        "**[作者主張]** 測試摘要，並討論讀取/寫入/同步、效能/performance 與 inline code `<table>`。",
        1,
    ).replace(
        "T = max(a, b)",
        "GET /api/v1/models?limit=10\n"
        "POST /v1/chat/completions#usage\n"
        "GET /api/v1/models;\n"
        "POST /generate\n"
        "/healthz\n"
        "/metrics\n"
        "/graphql",
        1,
    )
    validate_without_disk(legitimate_validation_claim)
    labelled_term_definition = draft.replace(
        f"## 16. {EXPECTED_SECTIONS[15]}\n\n**[分析]** 測試內容。（來源：§1 · PDF p.1）",
        f"## 16. {EXPECTED_SECTIONS[15]}\n\n"
        "- **[作者主張]** `KV`：指 key-value cache。（來源：§1 · PDF p.1）",
        1,
    )
    validate_without_disk(labelled_term_definition)
    validate_without_disk(
        draft.replace(
            "| 正式標題 | Formal Paper Title |",
            "| 正式標題 | Verified Legacy Formal Title |",
            1,
        ),
        allow_legacy_folder_title=True,
    )

    image_match = next(
        match for match in DIRECTIVE_RE.finditer(draft) if match.group(1) == "paper-image"
    )
    no_image_draft = draft.replace(
        image_match.group(0),
        "**[分析]** 本摘要未擷取圖表：測試摘要不需要圖片。（來源：§1 · PDF p.1）",
        1,
    )
    no_image_directives = validate_without_disk(no_image_draft)
    render_storage(no_image_draft, no_image_directives, markup)
    no_reason_image_draft = draft.replace(
        image_match.group(0),
        "**[分析]** 本摘要未擷取圖表。（來源：§1 · PDF p.1）",
        1,
    )
    vague_absence_image_draft = draft.replace(
        image_match.group(0),
        "論文未提供可編輯圖檔，因此未擷取。",
        1,
    )
    misleading_absence_image_draft = draft.replace(
        image_match.group(0),
        "**[作者主張]** 論文未提供圖表之外的證據。（來源：§1 · PDF p.1）",
        1,
    )
    unlabeled_image_claim_draft = draft.replace(
        image_match.group(0),
        image_match.group(0) + "\n\n此法完全消除排隊且沒有任何限制。",
        1,
    )

    attachment_match = DIRECTIVE_RE.search(draft)
    if attachment_match is None or attachment_match.group(1) != "paper-attachment":
        raise DraftError("self-test 找不到 PDF directive")
    attachment_block = attachment_match.group(0)
    wrong_attachment_section = (
        draft[: attachment_match.start()] + draft[attachment_match.end() :]
    ).replace(
        f"## 16. {EXPECTED_SECTIONS[15]}\n\n",
        f"## 16. {EXPECTED_SECTIONS[15]}\n\n{attachment_block}\n\n",
        1,
    )
    wrong_page_count_section = draft.replace(
        "| 頁數 | 共 1 頁 |", "| 頁數 | 見下一章 |", 1
    ).replace(
        "**[作者主張]** 測試摘要。（來源：§1 · PDF p.1）",
        "**[作者主張]** 測試摘要，共 1 頁。（來源：§1 · PDF p.1）",
        1,
    )
    negative_cases = {
        "headings hidden in code fence": "````markdown\n" + draft + "\n````\n",
        "mismatched image source": draft.replace(
            "§1 · PDF p.1 · Figure 1", "§1 · PDF p.1 · Table 9"
        ),
        "image label embedded in a larger token": draft.replace(
            "§1 · PDF p.1 · Figure 1", "§1 · PDF p.1 · NotFigure 1"
        ),
        "image label with Unicode prefix": draft.replace(
            "§1 · PDF p.1 · Figure 1", "§1 · PDF p.1 · 圖Figure 1"
        ),
        "PDF locator embedded in token": draft.replace(
            "§1 · PDF p.1 · Figure 1", "§1 · NotPDF p.1 · Figure 1"
        ),
        "junk after PDF page": draft.replace(
            "§1 · PDF p.1 · Figure 1", "§1 · PDF p.1junk · Figure 1"
        ),
        "empty image section locator": draft.replace(
            "§1 · PDF p.1 · Figure 1", "§ · PDF p.1 · Figure 1"
        ),
        "junk after image section locator": draft.replace(
            "§1 · PDF p.1 · Figure 1", "§1junk · PDF p.1 · Figure 1"
        ),
        "unbold evidence label": draft.replace(
            "**[作者主張]**", "[作者主張]", 1
        ),
        "unlabelled numeric claim": draft.replace(
            "**[作者主張]** 測試摘要。（來源：§1 · PDF p.1）",
            "**[作者主張]** 測試摘要。（來源：§1 · PDF p.1）未標記結果提升 999×。",
            1,
        ),
        "unlabelled qualitative claim": draft.replace(
            "**[作者主張]** 測試摘要。（來源：§1 · PDF p.1）",
            "**[作者主張]** 測試摘要。（來源：§1 · PDF p.1）此法完全消除排隊且沒有任何限制。",
            1,
        ),
        "not-provided phrase hiding a claim": draft.replace(
            "**[作者主張]** 測試摘要。（來源：§1 · PDF p.1）",
            "論文未提供誤差棒，但此法完全消除排隊且沒有任何限制。",
            1,
        ),
        "source prefix hiding a claim": draft.replace(
            "**[作者主張]** 測試摘要。（來源：§1 · PDF p.1）",
            "來源：§1 · PDF p.1，此法完全消除排隊且沒有任何限制。",
            1,
        ),
        "evidence source missing section": draft.replace(
            "**[作者主張]** 測試摘要。（來源：§1 · PDF p.1）",
            "**[作者主張]** 測試摘要。（來源：PDF p.1）",
            1,
        ),
        "wrong classification row": draft.replace(
            "| 分類 | Topic / Subtopic |", "| 分類 | Wrong / Classification |", 1
        ),
        "wrong formal title": draft.replace(
            "| 正式標題 | Formal Paper Title |", "| 正式標題 | Totally Wrong |", 1
        ),
        "meaningful punctuation lost from title": draft.replace(
            "| 正式標題 | Formal Paper Title |", "| 正式標題 | Formal Paper Title++ |", 1
        ),
        "invalid calendar date": draft.replace(
            "| 最後更新 | 2026-09-08 |", "| 最後更新 | 2026-02-31 |", 1
        ),
        "classification rationale without evidence": draft.replace(
            "| 分類理由 | **[分析]** 測試分類理由（來源：Abstract · PDF p.1） |",
            "| 分類理由 | plain |",
            1,
        ),
        "future last-updated date": draft.replace(
            "| 最後更新 | 2026-09-08 |", "| 最後更新 | 2099-12-31 |", 1
        ),
        "empty metadata value": draft.replace(
            "| 作者 | 測試作者 |", "| 作者 |  |", 1
        ),
        "three-column metadata row": draft.replace(
            "| 正式標題 | Formal Paper Title |", "| 正式標題 | 測試 | 論文 |", 1
        ),
        "PDF directive in wrong section": wrong_attachment_section,
        "page count in wrong section": wrong_page_count_section,
        "reference-style Markdown image": draft.replace(
            "**[作者主張]** 測試摘要。",
            "**[作者主張]** 測試摘要。 ![不允許][figure]",
            1,
        ),
        "canonical URL with unencoded parentheses": draft.replace(
            "https://example.com/paper?a=1&b=2",
            "https://example.com/paper_(v2)",
            1,
        ),
        "general HTTPS link with unencoded parentheses": draft.replace(
            "**[作者主張]** 測試摘要。",
            "**[作者主張]** [測試](https://example.com/item_(v2)) 摘要。",
            1,
        ),
        "escaped pipe inside table": draft.replace(
            "| 作者 | 測試作者 |", "| 作者 | p50 \\| p99 |", 1
        ),
        "raw HTML": draft.replace(
            "**[作者主張]** 測試摘要。",
            "**[作者主張]** 測試摘要。 <object data=\"x\"></object>",
            1,
        ),
        "Windows path": draft.replace(
            "**[作者主張]** 測試摘要。",
            "**[作者主張]** 測試摘要位於 C:/Users/example/paper。",
            1,
        ),
        "forward-slash UNC path": draft.replace(
            "**[作者主張]** 測試摘要。",
            "**[作者主張]** 測試摘要位於 //server/share/paper。",
            1,
        ),
        "mixed-separator UNC path": draft.replace(
            "**[作者主張]** 測試摘要。",
            "**[作者主張]** 測試摘要位於 \\\\server/share/paper。",
            1,
        ),
        "POSIX absolute path": draft.replace(
            "**[作者主張]** 測試摘要。",
            "**[作者主張]** 測試摘要位於 /home/user/paper.pdf。",
            1,
        ),
        "CJK-adjacent POSIX absolute path": draft.replace(
            "**[作者主張]** 測試摘要。",
            "**[作者主張]** 摘要來源位於/home/user/paper.pdf。",
            1,
        ),
        "single-component POSIX absolute path": draft.replace(
            "**[作者主張]** 測試摘要。",
            "**[作者主張]** 測試摘要位於 /tmp。",
            1,
        ),
        "relative Markdown link": draft.replace(
            "**[作者主張]** 測試摘要。",
            "**[作者主張]** [本地 PDF](paper.pdf) 的測試摘要。",
            1,
        ),
        "path hidden in fenced code": draft.replace(
            "T = max(a, b)", "C:/Users/example/paper",
            1,
        ),
        "POSIX path hidden in fenced code": draft.replace(
            "T = max(a, b)", "/data/user/paper.pdf",
            1,
        ),
        "paper image without evidence type": draft.replace(
            '"evidence": "分析", ', "", 1
        ),
        "no-image marker without reason": no_reason_image_draft,
        "vague not-provided image bypass": vague_absence_image_draft,
        "misleading no-image prefix": misleading_absence_image_draft,
        "unlabelled claim beside valid image": unlabeled_image_claim_draft,
        "unsupported H3": draft.replace(
            f"## 10. {EXPECTED_SECTIONS[9]}\n\n",
            f"## 10. {EXPECTED_SECTIONS[9]}\n\n### 此法完全消除排隊\n\n",
            1,
        ),
        "section 16 aggregate-source bypass": draft.replace(
            f"## 16. {EXPECTED_SECTIONS[15]}\n\n**[分析]** 測試內容。（來源：§1 · PDF p.1）",
            f"## 16. {EXPECTED_SECTIONS[15]}\n\n"
            "- 關鍵結論：方法提升 999×。\n"
            "- `KV`：測試術語。（來源：§1 · PDF p.1）",
            1,
        ),
        "section 16 term-claim bypass": draft.replace(
            f"## 16. {EXPECTED_SECTIONS[15]}\n\n**[分析]** 測試內容。（來源：§1 · PDF p.1）",
            f"## 16. {EXPECTED_SECTIONS[15]}\n\n"
            "- `Speedup`：方法提升 999×。\n"
            "- `KV`：指 key-value cache。（來源：§1 · PDF p.1）",
            1,
        ),
        "section 16 qualitative term-tail bypass": draft.replace(
            f"## 16. {EXPECTED_SECTIONS[15]}\n\n**[分析]** 測試內容。（來源：§1 · PDF p.1）",
            f"## 16. {EXPECTED_SECTIONS[15]}\n\n"
            "- `KV`：指 key-value cache，且方法完全消除排隊。（來源：§1 · PDF p.1）",
            1,
        ),
        "section 16 pure-looking term claim bypass": draft.replace(
            f"## 16. {EXPECTED_SECTIONS[15]}\n\n**[分析]** 測試內容。（來源：§1 · PDF p.1）",
            f"## 16. {EXPECTED_SECTIONS[15]}\n\n"
            "- `LayerKV`：指可解決所有排隊問題的方法。（來源：§1 · PDF p.1）",
            1,
        ),
        "invalid XML Unicode": draft + "\ud800",
        "duplicate JSON key": draft.replace(
            '"label": "開啟論文 PDF"',
            '"label": "開啟論文 PDF", "label": "開啟論文 PDF"',
            1,
        ),
    }
    for name, candidate in negative_cases.items():
        try:
            validate_without_disk(candidate)
        except DraftError:
            continue
        raise DraftError(f"self-test negative case unexpectedly passed: {name}")

    try:
        _validate_output_target(source, source, directives, overwrite_output=False)
    except DraftError:
        pass
    else:
        raise DraftError("self-test output/input collision unexpectedly passed")

    generated_output = paper_dir / "prior.storage.xhtml"
    path_type = type(generated_output)
    with (
        mock.patch.object(path_type, "exists", return_value=True),
        mock.patch.object(path_type, "is_dir", return_value=False),
        mock.patch.object(
            path_type,
            "read_text",
            return_value=STORAGE_GENERATOR_MARKER + "<p>old</p>",
        ),
    ):
        _validate_output_target(
            generated_output,
            source,
            directives,
            overwrite_output=True,
        )
    with (
        mock.patch.object(path_type, "exists", return_value=True),
        mock.patch.object(path_type, "is_dir", return_value=False),
        mock.patch.object(
            path_type,
            "read_text",
            return_value="<p>unrelated</p>\n" + STORAGE_GENERATOR_MARKER,
        ),
    ):
        try:
            _validate_output_target(
                generated_output,
                source,
                directives,
                overwrite_output=True,
            )
        except DraftError:
            pass
        else:
            raise DraftError("self-test unmarked overwrite unexpectedly passed")

    print("self-test passed")


def _default_project_root() -> Path:
    # scripts/ -> paper-reading-confluence/ -> skills/ -> .agents/ -> project root
    return Path(__file__).resolve().parents[4]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate confluence-summary.md and render Confluence storage XHTML."
    )
    parser.add_argument("--source", type=Path)
    parser.add_argument("--paper-directory", type=Path)
    parser.add_argument("--project-root", type=Path, default=_default_project_root())
    parser.add_argument("--atlassian-cli", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--overwrite-output",
        action="store_true",
        help="replace an existing generated .storage.xhtml after explicit review",
    )
    parser.add_argument(
        "--allow-unreferenced-images",
        action="store_true",
        help="allow curated assets/images files to remain outside this page",
    )
    parser.add_argument(
        "--allow-legacy-folder-title",
        action="store_true",
        help="allow a verified existing paper folder whose basename differs from the formal title",
    )
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    args = build_parser().parse_args()
    try:
        if args.self_test:
            run_self_test(args.atlassian_cli)
            return 0
        missing = [
            name
            for name, value in (
                ("--source", args.source),
                ("--paper-directory", args.paper_directory),
                ("--output", args.output),
            )
            if value is None
        ]
        if missing:
            raise DraftError("缺少必要參數：" + ", ".join(missing))
        report = prepare(
            args.source,
            args.paper_directory,
            args.project_root,
            args.atlassian_cli,
            args.output,
            overwrite_output=args.overwrite_output,
            allow_unreferenced_images=args.allow_unreferenced_images,
            allow_legacy_folder_title=args.allow_legacy_folder_title,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except DraftError as exc:
        print(f"validation failed:\n{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
