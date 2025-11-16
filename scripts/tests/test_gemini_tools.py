"""Unit tests for Gemini helper scripts."""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from scripts import setup_gemini_corpus, test_gemini_api


def test_basic_connection_handles_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure GeminiAPITester reports rate-limit warnings and falls back."""

    def fake_configure(*_, **__):
        return None

    class FakeModel:
        def __init__(self, model_name: str):
            self.model_name = model_name

        def generate_content(self, *_args, **_kwargs):
            if self.model_name == test_gemini_api.DEFAULT_MODEL:
                raise Exception("429 rate limit exceeded")  # noqa: BLE001
            return types.SimpleNamespace(text="ok")

    class FakeGenerationConfig:
        def __init__(self, **_kwargs):
            pass

    monkeypatch.setattr(test_gemini_api.genai, "configure", fake_configure)
    monkeypatch.setattr(test_gemini_api.genai, "GenerativeModel", FakeModel)
    monkeypatch.setattr(
        test_gemini_api.genai,
        "types",
        types.SimpleNamespace(GenerationConfig=FakeGenerationConfig),
    )

    tester = test_gemini_api.GeminiAPITester(api_key="A" * 40)
    result = tester.test_basic_connection()

    assert result.status == test_gemini_api.TestStatus.WARN
    assert "fallback" in result.message.lower()


def test_categorize_document_prefers_specific_category(tmp_path: Path) -> None:
    """Verify Cat Scale documents are categorized correctly with safe filenames."""

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    sample_file = source_dir / "Cat Scale Pricing Memo.pdf"
    sample_file.write_text("dummy content", encoding="utf-8")

    generator = setup_gemini_corpus.CorpusGenerator(source_dir, output_dir)
    metadata = generator._create_metadata(sample_file)

    assert metadata.category == "cat_scale"
    html = generator.generate_html(metadata)
    assert "Cat Scale pricing" in html

    sanitized = generator._sanitize_filename("Cat*Scale Price List!")
    assert sanitized == "CatScale_Price_List"

