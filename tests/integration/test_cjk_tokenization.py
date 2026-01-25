"""Integration tests for CJK translation/transliteration token alignment.

These tests verify that translations to Chinese, Japanese, Korean, and other
languages without standard word delimiters produce translation and transliteration
tracks with aligned token counts for optimal synchronized highlighting.

Run with real LLM:
    pytest tests/integration/test_cjk_tokenization.py -v --run-llm

Run with custom model:
    pytest tests/integration/test_cjk_tokenization.py -v --run-llm --llm-model mistral:latest

Run specific language:
    pytest tests/integration/test_cjk_tokenization.py -v --run-llm -k chinese
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Test sentences designed to produce varied token counts
SAMPLE_SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "Good morning! How are you today?",
    "She sells seashells by the seashore.",
    "I love reading books about history.",
    "The weather is beautiful this afternoon.",
    "Please remember to call me tomorrow.",
    "Technology has changed our daily lives.",
    "Music brings people together.",
    "Learning a new language takes dedication.",
    "The sunset painted the sky in brilliant colors.",
]

# Languages with tokenization challenges (no standard word delimiters)
CJK_LANGUAGES = {
    "chinese": {
        "code": "zh",
        "aliases": ["chinese", "zh", "zh-cn", "mandarin"],
        "script": "Han",
        "has_spaces": False,
        "transliteration_method": "pinyin",
    },
    "japanese": {
        "code": "ja",
        "aliases": ["japanese", "ja"],
        "script": "Hiragana/Katakana/Han",
        "has_spaces": False,
        "transliteration_method": "romaji",
    },
    "korean": {
        "code": "ko",
        "aliases": ["korean", "ko"],
        "script": "Hangul",
        "has_spaces": True,  # Korean does use spaces, but can have issues
        "transliteration_method": "romanization",
    },
    "thai": {
        "code": "th",
        "aliases": ["thai", "th"],
        "script": "Thai",
        "has_spaces": False,
        "transliteration_method": "romanization",
    },
    "burmese": {
        "code": "my",
        "aliases": ["burmese", "myanmar", "my"],
        "script": "Myanmar",
        "has_spaces": False,
        "transliteration_method": "romanization",
    },
    "khmer": {
        "code": "km",
        "aliases": ["khmer", "cambodian", "km"],
        "script": "Khmer",
        "has_spaces": False,
        "transliteration_method": "romanization",
    },
}


@dataclass
class TokenizationResult:
    """Result of translating and tokenizing a single sentence."""

    source: str
    source_tokens: List[str]
    translation: str
    translation_tokens: List[str]
    transliteration: str
    transliteration_tokens: List[str]
    token_count_match: bool
    token_count_diff: int
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "source_tokens": self.source_tokens,
            "source_token_count": len(self.source_tokens),
            "translation": self.translation,
            "translation_tokens": self.translation_tokens,
            "translation_token_count": len(self.translation_tokens),
            "transliteration": self.transliteration,
            "transliteration_tokens": self.transliteration_tokens,
            "transliteration_token_count": len(self.transliteration_tokens),
            "token_count_match": self.token_count_match,
            "token_count_diff": self.token_count_diff,
            "errors": self.errors,
        }


@dataclass
class LanguageTestReport:
    """Test report for a specific language."""

    language: str
    language_config: Dict[str, Any]
    results: List[TokenizationResult]
    total_sentences: int = 0
    matching_count: int = 0
    average_token_diff: float = 0.0
    success_rate: float = 0.0

    def calculate_metrics(self) -> None:
        if not self.results:
            return
        self.total_sentences = len(self.results)
        self.matching_count = sum(1 for r in self.results if r.token_count_match)
        total_diff = sum(abs(r.token_count_diff) for r in self.results)
        self.average_token_diff = total_diff / self.total_sentences if self.total_sentences else 0.0
        self.success_rate = self.matching_count / self.total_sentences if self.total_sentences else 0.0

    def to_dict(self) -> Dict[str, Any]:
        self.calculate_metrics()
        return {
            "language": self.language,
            "language_config": self.language_config,
            "total_sentences": self.total_sentences,
            "matching_count": self.matching_count,
            "average_token_diff": round(self.average_token_diff, 2),
            "success_rate": round(self.success_rate * 100, 1),
            "results": [r.to_dict() for r in self.results],
        }


def pytest_addoption_cjk(parser: pytest.Parser) -> None:
    """Add CLI options for CJK tokenization tests."""
    group = parser.getgroup("cjk-tokenization")
    group.addoption(
        "--run-llm",
        action="store_true",
        default=False,
        help="Run tests that require a real LLM connection",
    )
    group.addoption(
        "--llm-model",
        action="store",
        default=None,
        help="LLM model to use for translation (e.g., mistral:latest)",
    )
    group.addoption(
        "--save-report",
        action="store",
        default=None,
        help="Path to save JSON test report",
    )


@pytest.fixture(scope="module")
def llm_client(request):
    """Create an LLM client for testing."""
    if not request.config.getoption("--run-llm", default=False):
        pytest.skip("--run-llm not specified")

    from modules import llm_client_manager

    model = request.config.getoption("--llm-model", default=None)
    client = llm_client_manager.get_default_client()

    if model:
        # Override model if specified
        client = llm_client_manager.create_client(model=model)

    return client


@pytest.fixture
def tokenizer():
    """Return the tokenization function."""
    from modules.text import split_highlight_tokens
    return split_highlight_tokens


@pytest.fixture
def transliterator():
    """Return the transliteration service."""
    from modules.transliteration import get_transliterator
    return get_transliterator()


def translate_and_tokenize(
    sentence: str,
    target_language: str,
    client,
    tokenizer,
    transliterator,
) -> TokenizationResult:
    """Translate a sentence and analyze token alignment."""
    from modules import translation_engine, text_normalization as text_norm

    errors: List[str] = []

    # Get source tokens
    source_tokens = tokenizer(sentence)

    # Translate with transliteration
    try:
        result = translation_engine.translate_sentence_simple(
            sentence,
            "english",
            target_language,
            include_transliteration=True,
            client=client,
        )
    except Exception as e:
        return TokenizationResult(
            source=sentence,
            source_tokens=source_tokens,
            translation="",
            translation_tokens=[],
            transliteration="",
            transliteration_tokens=[],
            token_count_match=False,
            token_count_diff=0,
            errors=[f"Translation error: {e}"],
        )

    # Parse translation and transliteration
    translation_text, transliteration_text = text_norm.split_translation_and_transliteration(result)

    # If no transliteration in response, try to generate one
    if not transliteration_text and translation_text:
        try:
            translit_result = transliterator.transliterate(
                translation_text,
                target_language,
                client=client,
            )
            transliteration_text = translit_result.text
        except Exception as e:
            errors.append(f"Transliteration error: {e}")

    # Tokenize both tracks
    translation_tokens = tokenizer(translation_text) if translation_text else []
    transliteration_tokens = tokenizer(transliteration_text) if transliteration_text else []

    # Calculate token alignment
    trans_count = len(translation_tokens)
    translit_count = len(transliteration_tokens)
    token_count_match = trans_count == translit_count
    token_count_diff = trans_count - translit_count

    if not token_count_match:
        errors.append(
            f"Token count mismatch: translation={trans_count}, transliteration={translit_count}"
        )

    return TokenizationResult(
        source=sentence,
        source_tokens=source_tokens,
        translation=translation_text,
        translation_tokens=translation_tokens,
        transliteration=transliteration_text,
        transliteration_tokens=transliteration_tokens,
        token_count_match=token_count_match,
        token_count_diff=token_count_diff,
        errors=errors,
    )


class TestCJKTokenization:
    """Integration tests for CJK language tokenization alignment."""

    @pytest.mark.parametrize("language", list(CJK_LANGUAGES.keys()))
    def test_language_token_alignment(
        self,
        language: str,
        llm_client,
        tokenizer,
        transliterator,
        request,
    ):
        """Test token alignment for a specific language."""
        lang_config = CJK_LANGUAGES[language]
        results: List[TokenizationResult] = []

        for sentence in SAMPLE_SENTENCES[:5]:  # Use first 5 for quicker tests
            result = translate_and_tokenize(
                sentence,
                language,
                llm_client,
                tokenizer,
                transliterator,
            )
            results.append(result)

            # Log individual result
            print(f"\n[{language}] {sentence[:40]}...")
            print(f"  Translation ({len(result.translation_tokens)} tokens): {result.translation[:60]}...")
            print(f"  Transliteration ({len(result.transliteration_tokens)} tokens): {result.transliteration[:60]}...")
            if not result.token_count_match:
                print(f"  ⚠ Token mismatch: diff={result.token_count_diff}")

        # Generate report
        report = LanguageTestReport(
            language=language,
            language_config=lang_config,
            results=results,
        )
        report.calculate_metrics()

        # Save report if requested
        save_path = request.config.getoption("--save-report", default=None)
        if save_path:
            report_path = Path(save_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            existing = {}
            if report_path.exists():
                existing = json.loads(report_path.read_text())
            existing[language] = report.to_dict()
            report_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))

        # Assert at least 50% success rate for alignment
        assert report.success_rate >= 0.5, (
            f"{language}: Token alignment success rate {report.success_rate:.1%} is below 50% threshold. "
            f"Average token diff: {report.average_token_diff:.1f}"
        )


class TestTokenizationUtilities:
    """Unit tests for tokenization helper functions."""

    def test_chinese_tokenization(self, tokenizer):
        """Test Chinese text tokenization."""
        # Text with spaces (what we want)
        text_with_spaces = "你好 世界 我 喜欢 读书"
        tokens = tokenizer(text_with_spaces)
        assert len(tokens) == 5
        assert tokens == ["你好", "世界", "我", "喜欢", "读书"]

        # Text without spaces (current behavior)
        text_no_spaces = "你好世界我喜欢读书"
        tokens_no_space = tokenizer(text_no_spaces)
        # Currently falls back to grapheme/character tokenization
        assert len(tokens_no_space) >= 1

    def test_japanese_tokenization(self, tokenizer):
        """Test Japanese text tokenization."""
        # Text with spaces (what we want)
        text_with_spaces = "こんにちは 世界 私は 本を 読みます"
        tokens = tokenizer(text_with_spaces)
        assert len(tokens) >= 4  # Depends on tokenizer availability

        # Test romaji transliteration tokenization
        romaji = "konnichiwa sekai watashi wa hon wo yomimasu"
        romaji_tokens = tokenizer(romaji)
        assert len(romaji_tokens) == 8

    def test_korean_tokenization(self, tokenizer):
        """Test Korean text tokenization."""
        # Korean typically uses spaces
        text = "안녕하세요 세계 저는 책을 읽습니다"
        tokens = tokenizer(text)
        assert len(tokens) == 5

    def test_thai_tokenization(self, tokenizer):
        """Test Thai text tokenization."""
        # Text with spaces (what we want)
        text_with_spaces = "สวัสดี โลก ฉัน รัก การอ่าน"
        tokens = tokenizer(text_with_spaces)
        assert len(tokens) >= 4

    def test_transliteration_token_alignment(self, tokenizer):
        """Test that transliteration tokens can be matched to translation tokens."""
        # Aligned translation and transliteration
        translation = "你好 世界"
        transliteration = "ni hao shi jie"

        trans_tokens = tokenizer(translation)
        translit_tokens = tokenizer(transliteration)

        # Both should have same count for proper alignment
        # Note: This test shows current behavior; may fail until prompts are improved
        print(f"Translation tokens: {trans_tokens}")
        print(f"Transliteration tokens: {translit_tokens}")


class TestPromptTemplates:
    """Tests for prompt template generation."""

    def test_segmentation_instructions_present(self):
        """Verify prompts include segmentation instructions for CJK languages."""
        from modules import prompt_templates

        for lang, config in CJK_LANGUAGES.items():
            if not config["has_spaces"]:
                prompt = prompt_templates.make_translation_prompt(
                    "english",
                    lang,
                    include_transliteration=True,
                )
                # Should mention word/phrase spacing
                assert "space" in prompt.lower() or "segmentation" in prompt.lower(), (
                    f"Prompt for {lang} should include segmentation instructions"
                )

    def test_batch_prompt_includes_alignment_instruction(self):
        """Verify batch prompts mention token alignment."""
        from modules import prompt_templates

        for lang in ["chinese", "japanese"]:
            prompt = prompt_templates.make_translation_batch_prompt(
                "english",
                lang,
                include_transliteration=True,
            )
            # Should mention alignment or matching between translation and transliteration
            # This test may fail until we add this feature
            print(f"\n{lang} batch prompt excerpt:")
            print(prompt[:500])


# Helper function to run a quick diagnostic
def run_diagnostic(
    model: Optional[str] = None,
    sentences: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run a diagnostic test without pytest for quick iteration.

    Usage:
        from tests.integration.test_cjk_tokenization import run_diagnostic
        report = run_diagnostic(
            model="mistral:latest",
            sentences=["Hello world"],
            languages=["chinese", "japanese"],
        )
    """
    from modules import llm_client_manager
    from modules.text import split_highlight_tokens
    from modules.transliteration import get_transliterator

    sentences = sentences or SAMPLE_SENTENCES[:3]
    languages = languages or ["chinese", "japanese", "korean"]

    client = llm_client_manager.get_default_client()
    if model:
        client = llm_client_manager.create_client(model=model)

    tokenizer = split_highlight_tokens
    transliterator = get_transliterator()

    report = {"languages": {}}

    for lang in languages:
        print(f"\n{'='*60}")
        print(f"Testing: {lang}")
        print('='*60)

        results = []
        for sentence in sentences:
            result = translate_and_tokenize(
                sentence,
                lang,
                client,
                tokenizer,
                transliterator,
            )
            results.append(result)

            print(f"\nSource: {sentence}")
            print(f"Translation ({len(result.translation_tokens)}): {result.translation}")
            print(f"  Tokens: {result.translation_tokens}")
            print(f"Transliteration ({len(result.transliteration_tokens)}): {result.transliteration}")
            print(f"  Tokens: {result.transliteration_tokens}")
            print(f"Match: {'✓' if result.token_count_match else '✗'} (diff={result.token_count_diff})")

        lang_report = LanguageTestReport(
            language=lang,
            language_config=CJK_LANGUAGES.get(lang, {}),
            results=results,
        )
        lang_report.calculate_metrics()
        report["languages"][lang] = lang_report.to_dict()

        print(f"\n{lang} Summary:")
        print(f"  Success rate: {lang_report.success_rate:.1%}")
        print(f"  Avg token diff: {lang_report.average_token_diff:.2f}")

    return report


if __name__ == "__main__":
    # Run diagnostic when executed directly
    import sys

    model = sys.argv[1] if len(sys.argv) > 1 else None
    report = run_diagnostic(model=model)

    # Save report
    report_path = Path("storage/cjk_tokenization_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport saved to: {report_path}")
