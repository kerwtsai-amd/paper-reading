from __future__ import annotations

import hashlib
import shutil
import unittest
from pathlib import Path

from scripts import build_site


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BuildSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = PROJECT_ROOT / "_site.__tests__" / self._testMethodName
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
        source: str = "https://arxiv.org/abs/2401.12345v2",
    ) -> Path:
        paper_directory = self.root / topic / subtopic / paper
        paper_directory.mkdir(parents=True)
        (paper_directory / "summary.html").write_text(
            "<!doctype html><html lang=\"zh-Hant\"><head>"
            "<meta charset=\"utf-8\"><title>Fallback｜Paper Reading</title>"
            "</head><body><h1>Example &amp; Paper</h1>"
            f'<a href="{source}">論文頁面</a>'
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

        index = (output / "index.html").read_text(encoding="utf-8")
        self.assertIn('lang="zh-Hant"', index)
        self.assertIn('name="robots" content="noindex, noarchive"', index)
        self.assertIn("搜尋論文", index)
        self.assertIn("LLM Systems", index)
        self.assertIn("KV Cache", index)
        self.assertIn("Example &amp; Paper", index)

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
        self.assertNotIn(
            "Do not publish",
            (self.root / "_site" / "index.html").read_text(encoding="utf-8"),
        )

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
