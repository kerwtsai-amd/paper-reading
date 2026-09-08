from __future__ import annotations

import hashlib
import html
import shutil
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scripts import build_site


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SemanticHTMLParser(HTMLParser):
    """Collect semantic test hooks and links without depending on CSS/layout."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str]]] = []
        self.anchors: list[tuple[dict[str, str], str]] = []
        self.navigations: list[
            tuple[dict[str, str], list[tuple[dict[str, str], str]]]
        ] = []
        self._navigation_stack: list[int] = []
        self._anchor_attrs: dict[str, str] | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        self.elements.append((tag, attr_map))
        if tag == "nav":
            self.navigations.append((attr_map, []))
            self._navigation_stack.append(len(self.navigations) - 1)
        if tag == "a":
            self._anchor_attrs = attr_map
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._anchor_attrs is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_attrs is not None:
            anchor = (
                self._anchor_attrs,
                " ".join("".join(self._anchor_text).split()),
            )
            self.anchors.append(anchor)
            if self._navigation_stack:
                self.navigations[self._navigation_stack[-1]][1].append(anchor)
            self._anchor_attrs = None
            self._anchor_text = []
        if tag == "nav" and self._navigation_stack:
            self._navigation_stack.pop()


class BuildSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        test_key = hashlib.sha256(self._testMethodName.encode("utf-8")).hexdigest()[:12]
        self.root = PROJECT_ROOT / "_site.__tests__" / test_key
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)

    def tearDown(self) -> None:
        tests_root = PROJECT_ROOT / "_site.__tests__"
        if self.root.exists():
            shutil.rmtree(self.root)
        if tests_root.exists() and not any(tests_root.iterdir()):
            tests_root.rmdir()

    def _add_summary(
        self,
        *,
        topic: str = "LLM Systems",
        subtopic: str = "KV Cache",
        paper: str = "Example Paper",
        title: str = "Example & Paper",
        source: str = "https://arxiv.org/abs/2401.12345v2",
        updated: str | None = "2026-09-08",
        before_update_html: str = "",
        breadcrumb_html: str | None = None,
    ) -> Path:
        paper_directory = self.root / topic / subtopic / paper
        paper_directory.mkdir(parents=True)
        if breadcrumb_html is None:
            breadcrumb_html = (
                '<p class="breadcrumb"><span>Paper Reading</span>'
                '<span aria-hidden="true">/</span>'
                f"<span>{html.escape(topic)}</span>"
                '<span aria-hidden="true">/</span>'
                f"<span>{html.escape(subtopic)}</span></p>"
            )
        update_html = ""
        if updated is not None:
            update_html = (
                "<dl><div><dt>摘要更新</dt><dd>"
                f'<time datetime="{html.escape(updated, quote=True)}">'
                f"{html.escape(updated)}</time>"
                "</dd></div></dl>"
            )
        (paper_directory / "summary.html").write_text(
            "<!doctype html><html lang=\"zh-Hant\"><head>"
            "<meta charset=\"utf-8\"><title>Fallback｜Paper Reading</title>"
            f"</head><body>{breadcrumb_html}<h1>{html.escape(title)}</h1>"
            f'<a href="{source}">論文頁面</a>'
            f"{before_update_html}{update_html}"
            '<a href="Example%20Paper.pdf" download>↓ 開啟本地 PDF</a>'
            '<img src="assets/images/figure.png" alt="figure">'
            "</body></html>",
            encoding="utf-8",
        )
        (paper_directory / "Example Paper.pdf").write_bytes(b"%PDF-local-only")
        images = paper_directory / "assets" / "images"
        images.mkdir(parents=True)
        (images / "figure.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        (images / "unreferenced-secret.png").write_bytes(
            b"\x89PNG\r\n\x1a\nnot-for-publication"
        )
        (paper_directory / "assets" / "notes.css").write_text(
            "body {}\n", encoding="utf-8"
        )
        (paper_directory / "assets" / "appendix.pdf").write_bytes(b"%PDF-hidden")
        (paper_directory / "assets" / "AGENTS.md").write_text(
            "internal\n", encoding="utf-8"
        )
        return paper_directory

    @staticmethod
    def _parse_html(path: Path) -> SemanticHTMLParser:
        parser = SemanticHTMLParser()
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        return parser

    def _resolve_local_href(self, site: Path, page: Path, href: str) -> Path:
        parsed = urlsplit(html.unescape(href))
        self.assertFalse(parsed.scheme or parsed.netloc, href)
        self.assertFalse(parsed.path.startswith(("/", "\\")), href)
        target = (page.parent / Path(*unquote(parsed.path).split("/"))).resolve()
        try:
            target.relative_to(site.resolve())
        except ValueError:
            self.fail(f"Local link escapes the generated site: {page} -> {href}")
        if not parsed.path or parsed.path.endswith("/") or target.is_dir():
            target /= "index.html"
        return target

    def _paper_slug_from_link(
        self, site: Path, page: Path, attributes: dict[str, str]
    ) -> str:
        target = self._resolve_local_href(site, page, attributes["href"])
        relative = target.relative_to(site.resolve())
        self.assertEqual(relative.parts[0], "papers")
        self.assertEqual(relative.parts[-1], "index.html")
        self.assertEqual(len(relative.parts), 3)
        return relative.parts[1]

    @staticmethod
    def _snapshot(directory: Path) -> dict[str, str]:
        return {
            path.relative_to(directory).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(directory.rglob("*"))
            if path.is_file()
        }

    def test_builds_searchable_index_and_rewrites_local_pdf_links(self) -> None:
        self._add_summary()
        output = self.root / "_site"

        papers = build_site.build_site(self.root, output)

        self.assertEqual([paper.slug for paper in papers], ["arxiv-2401-12345"])
        published = output / "papers" / "arxiv-2401-12345" / "index.html"
        document = published.read_text(encoding="utf-8")
        self.assertIn("https://arxiv.org/pdf/2401.12345v2", document)
        self.assertNotIn("Example%20Paper.pdf", document)
        self.assertNotIn("本地 PDF", document)
        self.assertIn("原始來源", document)
        self.assertNotIn(" download", document)
        self.assertTrue(
            (output / "papers" / "arxiv-2401-12345" / "assets" / "images" / "figure.png").is_file()
        )
        self.assertFalse(
            (output / "papers" / "arxiv-2401-12345" / "assets" / "notes.css").exists()
        )
        self.assertFalse(
            (
                output
                / "papers"
                / "arxiv-2401-12345"
                / "assets"
                / "images"
                / "unreferenced-secret.png"
            ).exists()
        )
        self.assertFalse(any(path.suffix.casefold() == ".pdf" for path in output.rglob("*")))
        self.assertFalse(any(path.name.casefold() == "agents.md" for path in output.rglob("*")))

        homepage_path = output / "index.html"
        homepage = homepage_path.read_text(encoding="utf-8")
        self.assertIn('lang="zh-Hant"', homepage)
        self.assertIn('name="robots" content="noindex, noarchive"', homepage)
        homepage_parser = self._parse_html(homepage_path)
        self.assertTrue(
            any(
                attrs.get("href") == "library/"
                and "library-cta" in attrs.get("class", "").split()
                for attrs, _ in homepage_parser.anchors
            )
        )
        self.assertTrue(
            any(
                tag == "article"
                and attrs.get("data-latest-paper") == "arxiv-2401-12345"
                for tag, attrs in homepage_parser.elements
            )
        )

        library_path = output / "library" / "index.html"
        library = library_path.read_text(encoding="utf-8")
        self.assertIn('lang="zh-Hant"', library)
        self.assertIn('name="robots" content="noindex, noarchive"', library)
        self.assertIn("搜尋全部論文", library)
        self.assertIn("LLM Systems", library)
        self.assertNotIn("Example%20Paper.pdf", library)

    def test_homepage_shows_exactly_three_latest_summary_updates(self) -> None:
        fixtures = (
            {
                "topic": "Newest Topic",
                "subtopic": "Serving",
                "paper": "Newest Directory",
                "title": "Newest Paper",
                "source": "https://arxiv.org/abs/2601.00001",
                "updated": "2026-09-10",
            },
            {
                "topic": "Alpha Topic",
                "subtopic": "Serving",
                "paper": "Alpha Directory",
                "title": "Same Title",
                "source": "https://arxiv.org/abs/2601.00002",
                "updated": "2026-09-09",
            },
            {
                "topic": "Beta Topic",
                "subtopic": "Serving",
                "paper": "Beta Directory",
                "title": "Same Title",
                "source": "https://arxiv.org/abs/2601.00003",
                "updated": "2026-09-09",
            },
            {
                "topic": "Fourth Topic",
                "subtopic": "Serving",
                "paper": "Fourth Directory",
                "title": "Fourth Paper",
                "source": "https://arxiv.org/abs/2601.00004",
                "updated": "2026-09-08",
                "before_update_html": (
                    '<p>Published <time datetime="2099-01-01">2099</time></p>'
                ),
            },
            {
                "topic": "Old Topic",
                "subtopic": "Serving",
                "paper": "Old Directory",
                "title": "Old Paper",
                "source": "https://arxiv.org/abs/2601.00005",
                "updated": "2026-09-07",
            },
        )
        for fixture in fixtures:
            self._add_summary(**fixture)

        output = self.root / "_site"
        papers = build_site.build_site(self.root, output)
        slug_by_directory = {paper.directory_name: paper.slug for paper in papers}
        homepage = self._parse_html(output / "index.html")
        latest_slugs = [
            attrs["data-latest-paper"]
            for tag, attrs in homepage.elements
            if tag == "article" and "data-latest-paper" in attrs
        ]

        self.assertEqual(
            latest_slugs,
            [
                slug_by_directory["Newest Directory"],
                slug_by_directory["Alpha Directory"],
                slug_by_directory["Beta Directory"],
            ],
        )
        self.assertEqual(len(latest_slugs), 3)
        homepage_document = (output / "index.html").read_text(encoding="utf-8")
        for slug in latest_slugs:
            self.assertIn(f'href="papers/{slug}/"', homepage_document)
            self.assertTrue((output / "papers" / slug / "index.html").is_file())
        self.assertNotIn(
            f'data-latest-paper="{slug_by_directory["Fourth Directory"]}"',
            homepage_document,
        )
        self.assertNotIn(
            f'data-latest-paper="{slug_by_directory["Old Directory"]}"',
            homepage_document,
        )

        library_paper_slugs = {
            self._paper_slug_from_link(output, page, attrs)
            for page in (output / "library").rglob("index.html")
            for attrs, _ in self._parse_html(page).anchors
            if attrs.get("data-folder-kind") == "paper"
        }
        self.assertEqual(library_paper_slugs, set(slug_by_directory.values()))

    def test_homepage_recent_folders_use_newest_child_and_deterministic_ties(
        self,
    ) -> None:
        fixtures = (
            ("Zulu Topic", "Hot Folder", "Hot New", "Hot New", "2602.00001", "2026-09-10"),
            ("Zulu Topic", "Hot Folder", "Hot Old", "Hot Old", "2602.00002", "2026-08-01"),
            ("Alpha Topic", "Tie Folder", "Tie A", "Tie A", "2602.00003", "2026-09-09"),
            ("Beta Topic", "Tie Folder", "Tie B", "Tie B", "2602.00004", "2026-09-09"),
            ("Gamma Topic", "Older Folder", "Older", "Older", "2602.00005", "2026-09-08"),
        )
        for topic, subtopic, paper, title, arxiv_id, updated in fixtures:
            self._add_summary(
                topic=topic,
                subtopic=subtopic,
                paper=paper,
                title=title,
                source=f"https://arxiv.org/abs/{arxiv_id}",
                updated=updated,
            )

        output = self.root / "_site"
        build_site.build_site(self.root, output)
        homepage_path = output / "index.html"
        recent = [
            attrs
            for attrs, _ in self._parse_html(homepage_path).anchors
            if "data-recent-folder" in attrs
        ]

        self.assertEqual(
            [(item["data-topic"], item["data-subtopic"]) for item in recent],
            [
                ("Zulu Topic", "Hot Folder"),
                ("Alpha Topic", "Tie Folder"),
                ("Beta Topic", "Tie Folder"),
            ],
        )
        self.assertEqual(len(recent), 3)
        self.assertEqual(
            len({(item["data-topic"], item["data-subtopic"]) for item in recent}),
            3,
        )
        for item in recent:
            self.assertFalse(item["href"].startswith("/"), item["href"])
            self.assertTrue(
                self._resolve_local_href(output, homepage_path, item["href"]).is_file()
            )

    def test_library_drills_down_from_topic_to_subtopic_to_stable_paper(self) -> None:
        fixtures = (
            ("AI Systems", "KV Cache", "Cache Paper", "Cache Paper", "2603.00001"),
            ("AI Systems", "Scheduling", "Queue Paper", "Queue Paper", "2603.00002"),
            ("模型系統", "推論服務", "中文論文", "中文論文", "2603.00003"),
        )
        for topic, subtopic, paper, title, arxiv_id in fixtures:
            self._add_summary(
                topic=topic,
                subtopic=subtopic,
                paper=paper,
                title=title,
                source=f"https://arxiv.org/abs/{arxiv_id}",
            )

        output = self.root / "_site"
        papers = build_site.build_site(self.root, output)
        expected_slugs = {paper.slug for paper in papers}
        homepage_path = output / "index.html"
        homepage = self._parse_html(homepage_path)
        ctas = [
            attrs
            for attrs, _ in homepage.anchors
            if "library-cta" in attrs.get("class", "").split()
        ]
        self.assertEqual([attrs["href"] for attrs in ctas], ["library/"])
        library_path = self._resolve_local_href(output, homepage_path, "library/")
        self.assertTrue(library_path.is_file())

        topic_links = [
            attrs
            for attrs, _ in self._parse_html(library_path).anchors
            if attrs.get("data-folder-kind") == "topic"
        ]
        self.assertEqual(
            {attrs["data-topic"] for attrs in topic_links},
            {"AI Systems", "模型系統"},
        )

        found_subtopics: set[tuple[str, str]] = set()
        found_papers: set[str] = set()
        for topic_link in topic_links:
            self.assertFalse(topic_link["href"].startswith("/"))
            topic_page = self._resolve_local_href(
                output, library_path, topic_link["href"]
            )
            self.assertTrue(topic_page.is_file())
            subtopic_links = [
                attrs
                for attrs, _ in self._parse_html(topic_page).anchors
                if attrs.get("data-folder-kind") == "subtopic"
            ]
            for subtopic_link in subtopic_links:
                self.assertEqual(
                    subtopic_link["data-topic"], topic_link["data-topic"]
                )
                found_subtopics.add(
                    (subtopic_link["data-topic"], subtopic_link["data-subtopic"])
                )
                self.assertFalse(subtopic_link["href"].startswith("/"))
                subtopic_page = self._resolve_local_href(
                    output, topic_page, subtopic_link["href"]
                )
                self.assertTrue(subtopic_page.is_file())
                paper_links = [
                    attrs
                    for attrs, _ in self._parse_html(subtopic_page).anchors
                    if attrs.get("data-folder-kind") == "paper"
                ]
                for paper_link in paper_links:
                    slug = self._paper_slug_from_link(
                        output, subtopic_page, paper_link
                    )
                    found_papers.add(slug)
                    self.assertFalse(paper_link["href"].startswith("/"))
                    self.assertEqual(
                        self._resolve_local_href(
                            output, subtopic_page, paper_link["href"]
                        ),
                        (output / "papers" / slug / "index.html").resolve(),
                    )

        self.assertEqual(
            found_subtopics,
            {
                ("AI Systems", "KV Cache"),
                ("AI Systems", "Scheduling"),
                ("模型系統", "推論服務"),
            },
        )
        self.assertEqual(found_papers, expected_slugs)

    def test_published_paper_breadcrumb_links_the_generated_hierarchy(self) -> None:
        source_breadcrumb = (
            '<p class="breadcrumb"><span>Paper Reading</span>'
            '<span aria-hidden="true">/</span><span>Wrong Topic</span>'
            '<span aria-hidden="true">/</span><span>Wrong Subtopic</span></p>'
        )
        paper_directory = self._add_summary(
            topic="LLM Systems",
            subtopic="KV Cache",
            paper="Breadcrumb Paper",
            title="Breadcrumb Paper",
            source="https://arxiv.org/abs/2603.10001",
            breadcrumb_html=source_breadcrumb,
        )
        source_summary = paper_directory / "summary.html"
        source_before_build = source_summary.read_bytes()
        output = self.root / "_site"

        papers = build_site.build_site(self.root, output)

        self.assertEqual(source_summary.read_bytes(), source_before_build)
        published_path = output / "papers" / papers[0].slug / "index.html"
        published_document = published_path.read_text(encoding="utf-8")
        self.assertNotIn("Wrong Topic", published_document)
        self.assertNotIn("Wrong Subtopic", published_document)
        published = self._parse_html(published_path)
        breadcrumb_candidates = [
            anchors
            for attributes, anchors in published.navigations
            if attributes.get("aria-label") == "麵包屑"
        ]
        self.assertEqual(len(breadcrumb_candidates), 1)
        breadcrumb = breadcrumb_candidates[0]
        self.assertEqual(
            [text for _, text in breadcrumb],
            ["首頁", "論文閱讀儲藏庫", "LLM Systems", "KV Cache"],
        )

        library_path = output / "library" / "index.html"
        topic_link = next(
            attributes
            for attributes, _ in self._parse_html(library_path).anchors
            if attributes.get("data-folder-kind") == "topic"
            and attributes.get("data-topic") == "LLM Systems"
        )
        topic_path = self._resolve_local_href(
            output, library_path, topic_link["href"]
        )
        subtopic_link = next(
            attributes
            for attributes, _ in self._parse_html(topic_path).anchors
            if attributes.get("data-folder-kind") == "subtopic"
            and attributes.get("data-subtopic") == "KV Cache"
        )
        subtopic_path = self._resolve_local_href(
            output, topic_path, subtopic_link["href"]
        )
        expected_targets = [
            (output / "index.html").resolve(),
            library_path.resolve(),
            topic_path.resolve(),
            subtopic_path.resolve(),
        ]
        actual_targets: list[Path] = []
        for attributes, _ in breadcrumb:
            href = attributes["href"]
            self.assertFalse(urlsplit(href).scheme or urlsplit(href).netloc, href)
            self.assertFalse(href.startswith(("/", "\\")), href)
            target = self._resolve_local_href(output, published_path, href)
            self.assertTrue(target.is_file(), href)
            actual_targets.append(target)
        self.assertEqual(actual_targets, expected_targets)

    def test_folder_routes_are_collision_safe_for_punctuation_and_chinese(self) -> None:
        fixtures = (
            ("AI & ML", "KV.Cache", "Amp Dot", "2604.00001"),
            ("AI & ML", "KV Cache", "Amp Space", "2604.00002"),
            ("AI ML", "Serving", "Plain", "2604.00003"),
            ("模型系統", "推論服務", "Chinese Solid", "2604.00004"),
            ("模型 系統", "推論服務", "Chinese Space", "2604.00005"),
        )
        for topic, subtopic, title, arxiv_id in fixtures:
            self._add_summary(
                topic=topic,
                subtopic=subtopic,
                paper=title,
                title=title,
                source=f"https://arxiv.org/abs/{arxiv_id}",
            )

        output = self.root / "_site"
        build_site.build_site(self.root, output)
        library_path = output / "library" / "index.html"
        topic_links = [
            attrs
            for attrs, _ in self._parse_html(library_path).anchors
            if attrs.get("data-folder-kind") == "topic"
        ]
        self.assertEqual(len(topic_links), 4)
        self.assertEqual(len({attrs["href"] for attrs in topic_links}), 4)
        self.assertEqual(
            {attrs["data-topic"] for attrs in topic_links},
            {"AI & ML", "AI ML", "模型系統", "模型 系統"},
        )

        subtopics_by_topic: dict[str, list[dict[str, str]]] = {}
        for topic_link in topic_links:
            topic_page = self._resolve_local_href(
                output, library_path, topic_link["href"]
            )
            self.assertTrue(topic_page.is_file())
            subtopics_by_topic[topic_link["data-topic"]] = [
                attrs
                for attrs, _ in self._parse_html(topic_page).anchors
                if attrs.get("data-folder-kind") == "subtopic"
            ]

        colliding_subtopics = subtopics_by_topic["AI & ML"]
        self.assertEqual(
            {attrs["data-subtopic"] for attrs in colliding_subtopics},
            {"KV.Cache", "KV Cache"},
        )
        self.assertEqual(len({attrs["href"] for attrs in colliding_subtopics}), 2)
        for links in subtopics_by_topic.values():
            for link in links:
                topic_link = next(
                    candidate
                    for candidate in topic_links
                    if candidate["data-topic"] == link["data-topic"]
                )
                topic_page = self._resolve_local_href(
                    output, library_path, topic_link["href"]
                )
                subtopic_page = self._resolve_local_href(
                    output, topic_page, link["href"]
                )
                self.assertTrue(subtopic_page.is_file())
                paper_slugs = [
                    self._paper_slug_from_link(output, subtopic_page, attrs)
                    for attrs, _ in self._parse_html(subtopic_page).anchors
                    if attrs.get("data-folder-kind") == "paper"
                ]
                self.assertEqual(len(set(paper_slugs)), 1)

    def test_reclassification_preserves_the_stable_paper_url(self) -> None:
        original_directory = self._add_summary(
            topic="Old Topic",
            subtopic="Old Subtopic",
            paper="Movable Paper",
            title="Movable Paper",
            source="https://arxiv.org/abs/2605.00001v2",
        )
        output = self.root / "_site"

        first_papers = build_site.build_site(self.root, output)
        first_slug = first_papers[0].slug
        first_public_path = output / "papers" / first_slug / "index.html"
        self.assertTrue(first_public_path.is_file())

        new_parent = self.root / "New Topic" / "New Subtopic"
        new_parent.mkdir(parents=True)
        shutil.move(str(original_directory), str(new_parent / "Movable Paper"))
        second_papers = build_site.build_site(self.root, output)

        self.assertEqual([paper.slug for paper in second_papers], [first_slug])
        self.assertTrue(first_public_path.is_file())
        library_documents = "\n".join(
            page.read_text(encoding="utf-8")
            for page in sorted((output / "library").rglob("index.html"))
        )
        self.assertIn("New Topic", library_documents)
        self.assertIn("New Subtopic", library_documents)
        self.assertNotIn("Old Topic", library_documents)
        self.assertNotIn("Old Subtopic", library_documents)
        paper_links = [
            (page, attrs)
            for page in (output / "library").rglob("index.html")
            for attrs, _ in self._parse_html(page).anchors
            if attrs.get("data-folder-kind") == "paper"
        ]
        self.assertTrue(paper_links)
        self.assertEqual(
            {
                self._paper_slug_from_link(output, page, attrs)
                for page, attrs in paper_links
            },
            {first_slug},
        )
        for page, attrs in paper_links:
            self.assertEqual(
                self._resolve_local_href(output, page, attrs["href"]),
                first_public_path.resolve(),
            )

    def test_requires_exactly_one_iso_summary_update_date(self) -> None:
        paper_directory = self._add_summary()
        summary = paper_directory / "summary.html"
        valid_document = summary.read_text(encoding="utf-8")
        update_start = valid_document.index("<dl><div><dt>摘要更新")
        update_end = valid_document.index("</dl>", update_start) + len("</dl>")
        update_block = valid_document[update_start:update_end]
        cases = {
            "missing": valid_document[:update_start] + valid_document[update_end:],
            "duplicate": valid_document.replace(
                "</body>", update_block + "</body>"
            ),
            "non_iso": valid_document.replace(
                'datetime="2026-09-08"', 'datetime="2026/09/08"'
            ),
        }

        for name, document in cases.items():
            with self.subTest(name=name):
                summary.write_text(document, encoding="utf-8")
                with self.assertRaises(build_site.BuildError):
                    build_site.build_site(self.root, self.root / "_site")

    def test_all_generated_navigation_keeps_private_paths_out(self) -> None:
        self._add_summary()
        output = self.root / "_site"
        build_site.build_site(self.root, output)

        for generated_path in output.rglob("*"):
            relative = generated_path.relative_to(output).as_posix()
            self.assertNotEqual(generated_path.suffix.casefold(), ".pdf", relative)
            self.assertNotEqual(generated_path.name.casefold(), "agents.md", relative)
            self.assertNotIn(".agents", (part.casefold() for part in generated_path.parts))

        for page in output.rglob("*.html"):
            document = page.read_text(encoding="utf-8")
            lowered = document.casefold()
            self.assertNotIn("example%20paper.pdf", lowered, page.as_posix())
            self.assertNotIn("agents.md", lowered, page.as_posix())
            self.assertNotIn(".agents", lowered, page.as_posix())
            self.assertNotIn("file:", lowered, page.as_posix())
            self.assertNotIn(str(self.root).casefold(), lowered, page.as_posix())
            self.assertNotIn(" download", lowered, page.as_posix())

            parser = self._parse_html(page)
            references = [
                value
                for tag, attrs in parser.elements
                for name, value in attrs.items()
                if (tag == "a" and name == "href")
                or (tag == "img" and name == "src")
            ]
            for reference in references:
                parsed = urlsplit(html.unescape(reference))
                if parsed.scheme or parsed.netloc:
                    self.assertIn(parsed.scheme, {"http", "https"}, reference)
                    self.assertTrue(parsed.netloc, reference)
                    continue
                self.assertFalse(reference.startswith(("/", "\\")), reference)
                self.assertNotEqual(Path(unquote(parsed.path)).suffix.casefold(), ".pdf")
                self.assertTrue(
                    self._resolve_local_href(output, page, reference).is_file(),
                    f"Broken local reference in {page}: {reference}",
                )

        self.assertTrue(
            (
                output
                / "papers"
                / "arxiv-2401-12345"
                / "assets"
                / "images"
                / "figure.png"
            ).is_file()
        )
        self.assertFalse(
            any(path.name == "unreferenced-secret.png" for path in output.rglob("*"))
        )

    def test_adversarial_summary_references_fail_closed(self) -> None:
        paper_directory = self._add_summary()
        summary = paper_directory / "summary.html"
        baseline = summary.read_text(encoding="utf-8")
        cases = {
            "root_relative": '<a href="/private/report.html">root</a>',
            "escaping": '<a href="../../../AGENTS.md">escape</a>',
            "missing_local": '<a href="notes/missing.html">missing</a>',
            "file_scheme": '<a href="file:///C:/Windows/win.ini">file</a>',
            "javascript_scheme": '<a href="javascript:alert(1)">script</a>',
            "data_scheme": (
                '<a href="data:text/html;base64,PHNjcmlwdD4=">data</a>'
            ),
            "missing_fragment": '<a href="#not-present">missing fragment</a>',
            "empty_fragment": '<a href="#">empty fragment</a>',
            "malformed_fragment_escape": '<a href="#bad%ZZ">bad fragment</a>',
        }

        for name, markup in cases.items():
            with self.subTest(name=name):
                summary.write_text(
                    baseline.replace("</body>", markup + "</body>"),
                    encoding="utf-8",
                )
                with self.assertRaises(build_site.BuildError):
                    build_site.build_site(self.root, self.root / "_site")

    def test_safe_summary_references_and_generated_navigation_pass(self) -> None:
        safe_markup = (
            '<a href="#main-content">Skip</a>'
            '<main id="main-content"><a href="#evidence">Evidence</a>'
            '<div id="evidence">Evidence target</div></main>'
            '<a href="assets/images/figure.png">Open generated figure</a>'
        )
        paper_directory = self._add_summary(before_update_html=safe_markup)
        summary = paper_directory / "summary.html"
        source_document = summary.read_text(encoding="utf-8").replace(
            "</head>",
            '<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>'
            "</head>",
        )
        summary.write_text(source_document, encoding="utf-8")
        output = self.root / "_site"

        papers = build_site.build_site(self.root, output)

        published_path = output / "papers" / papers[0].slug / "index.html"
        published = published_path.read_text(encoding="utf-8")
        self.assertIn('href="#main-content"', published)
        self.assertIn('href="#evidence"', published)
        self.assertIn(
            'src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"',
            published,
        )
        self.assertIn("https://arxiv.org/pdf/2401.12345v2", published)
        self.assertNotIn("Example%20Paper.pdf", published)
        self.assertTrue(
            (
                output
                / "papers"
                / papers[0].slug
                / "assets"
                / "images"
                / "figure.png"
            ).is_file()
        )

        for page in output.rglob("*.html"):
            for tag, attributes in self._parse_html(page).elements:
                for attribute_name in ("href", "src"):
                    reference = attributes.get(attribute_name)
                    if reference is None:
                        continue
                    parsed = urlsplit(html.unescape(reference))
                    if parsed.scheme or parsed.netloc:
                        self.assertEqual(parsed.scheme, "https", reference)
                        self.assertTrue(parsed.netloc, reference)
                        continue
                    self.assertFalse(reference.startswith(("/", "\\")), reference)
                    self.assertTrue(
                        self._resolve_local_href(output, page, reference).is_file(),
                        f"Broken {tag} reference in {page}: {reference}",
                    )

    def test_build_is_deterministic_and_removes_stale_output(self) -> None:
        self._add_summary()
        output = self.root / "_site"

        build_site.build_site(self.root, output)
        first = self._snapshot(output)
        (output / "stale.txt").write_text("stale", encoding="utf-8")
        build_site.build_site(self.root, output)
        second = self._snapshot(output)

        self.assertEqual(first, second)
        self.assertFalse((output / "stale.txt").exists())

    def test_ignores_summaries_outside_the_three_level_layout(self) -> None:
        self._add_summary()
        invalid = self.root / "Too" / "Shallow"
        invalid.mkdir(parents=True)
        (invalid / "summary.html").write_text(
            "<h1>Do not publish</h1>", encoding="utf-8"
        )

        papers = build_site.build_site(self.root, self.root / "_site")

        self.assertEqual(len(papers), 1)
        generated_html = "\n".join(
            page.read_text(encoding="utf-8")
            for page in (self.root / "_site").rglob("*.html")
        )
        self.assertNotIn("Do not publish", generated_html)

    def test_rejects_local_pdf_link_without_a_canonical_source(self) -> None:
        self._add_summary(source="#paper-info")

        with self.assertRaisesRegex(build_site.BuildError, "[Nn]o canonical"):
            build_site.build_site(self.root, self.root / "_site")

    def test_rejects_a_missing_relative_image(self) -> None:
        paper_directory = self._add_summary()
        (paper_directory / "assets" / "images" / "figure.png").unlink()

        with self.assertRaisesRegex(build_site.BuildError, "does not exist"):
            build_site.build_site(self.root, self.root / "_site")

    def test_arxiv_version_comes_only_from_a_canonical_anchor(self) -> None:
        paper_directory = self._add_summary(
            source="https://arxiv.org/abs/2401.12345v1"
        )
        summary = paper_directory / "summary.html"
        summary.write_text(
            summary.read_text(encoding="utf-8").replace(
                "</body>", "<p>比較文字 2401.12345v99</p></body>"
            ),
            encoding="utf-8",
        )

        build_site.build_site(self.root, self.root / "_site")

        published = (
            self.root / "_site" / "papers" / "arxiv-2401-12345" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("https://arxiv.org/pdf/2401.12345v1", published)
        self.assertNotIn("https://arxiv.org/pdf/2401.12345v99", published)

    def test_canonical_doi_beats_unrelated_repeated_arxiv_links(self) -> None:
        paper_directory = self._add_summary(
            source="https://doi.org/10.1000/main-paper"
        )
        summary = paper_directory / "summary.html"
        related_links = (
            '<a href="https://arxiv.org/abs/2501.00001">Related A</a>'
            '<a href="https://arxiv.org/pdf/2501.00001">Related A PDF</a>'
            '<a href="https://arxiv.org/abs/2501.00001">Related A again</a>'
            '<a href="https://arxiv.org/abs/2501.00002">Related B</a>'
        )
        summary.write_text(
            summary.read_text(encoding="utf-8").replace(
                "</body>", related_links + "</body>"
            ),
            encoding="utf-8",
        )

        papers = build_site.build_site(self.root, self.root / "_site")

        self.assertEqual(papers[0].source.kind, "doi")
        self.assertEqual(papers[0].source.url, "https://doi.org/10.1000/main-paper")
        published = (
            self.root / "_site" / "papers" / papers[0].slug / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn('href="https://doi.org/10.1000/main-paper"', published)

    def test_canonical_arxiv_beats_multiple_related_arxiv_links(self) -> None:
        paper_directory = self._add_summary(
            source="https://arxiv.org/abs/2401.12345v2"
        )
        summary = paper_directory / "summary.html"
        canonical = (
            '<a href="https://arxiv.org/abs/2401.12345v2">論文頁面</a>'
        )
        related_links = (
            '<a href="https://arxiv.org/abs/2501.00001">Related A</a>'
            '<a href="https://arxiv.org/pdf/2501.00001">Related A PDF</a>'
            '<a href="https://arxiv.org/pdf/2501.00001">Related A PDF again 1</a>'
            '<a href="https://arxiv.org/pdf/2501.00001">Related A PDF again 2</a>'
            '<a href="https://arxiv.org/pdf/2501.00001">Related A PDF again 3</a>'
            '<a href="https://arxiv.org/pdf/2501.00001">Related A PDF again 4</a>'
            '<a href="https://arxiv.org/abs/2501.00002">Related B</a>'
            '<a href="https://arxiv.org/abs/2501.00003">Related C</a>'
        )
        summary.write_text(
            summary.read_text(encoding="utf-8").replace(
                canonical, related_links + canonical
            ),
            encoding="utf-8",
        )

        papers = build_site.build_site(self.root, self.root / "_site")

        self.assertEqual(papers[0].source.kind, "arxiv")
        self.assertEqual(
            papers[0].source.url, "https://arxiv.org/pdf/2401.12345v2"
        )

    def test_refuses_a_symlinked_output(self) -> None:
        self._add_summary()
        outside = PROJECT_ROOT / "_site.__symlink-target__"
        target = outside / "_site"
        output = self.root / "_site"
        try:
            target.mkdir(parents=True, exist_ok=True)
            marker = target / "keep.txt"
            marker.write_text("keep", encoding="utf-8")
            try:
                output.symlink_to(target, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"Directory symlinks are unavailable: {exc}")

            with self.assertRaisesRegex(build_site.BuildError, "symlinked output"):
                build_site.build_site(self.root, output)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
        finally:
            if output.is_symlink():
                output.unlink()
            if outside.exists():
                shutil.rmtree(outside)


if __name__ == "__main__":
    unittest.main()
