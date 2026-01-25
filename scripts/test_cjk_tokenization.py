#!/usr/bin/env python3
"""Quick diagnostic script to test CJK tokenization alignment.

Usage:
    # Test with default model (mistral-large-3)
    python scripts/test_cjk_tokenization.py

    # Test specific languages
    python scripts/test_cjk_tokenization.py --languages chinese japanese

    # Test with specific sentences
    python scripts/test_cjk_tokenization.py --sentence "Hello world"

    # Generate full report
    python scripts/test_cjk_tokenization.py --report storage/cjk_report.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules import translation_engine, text_normalization as text_norm
from modules import llm_client_manager
from modules.text import split_highlight_tokens, align_token_counts
from modules.transliteration import get_transliterator


DEFAULT_SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "Good morning! How are you today?",
    "I love reading books about history.",
    "Technology has changed our daily lives.",
    "Learning a new language takes dedication.",
]

CJK_LANGUAGES = ["chinese", "japanese", "korean", "thai"]


def test_translation(
    sentence: str,
    target_language: str,
    client,
    transliterator,
    verbose: bool = True,
) -> dict:
    """Test a single translation and return metrics."""
    result = {
        "source": sentence,
        "target_language": target_language,
        "translation": "",
        "transliteration": "",
        "trans_tokens": [],
        "translit_tokens": [],
        "trans_count": 0,
        "translit_count": 0,
        "aligned": False,
        "diff": 0,
        "error": None,
    }

    try:
        # Translate
        raw_result = translation_engine.translate_sentence_simple(
            sentence,
            "english",
            target_language,
            include_transliteration=True,
            client=client,
        )

        # Parse translation and transliteration
        translation_text, transliteration_text = text_norm.split_translation_and_transliteration(raw_result)

        # If no transliteration, generate one
        if translation_text and not transliteration_text:
            translit_result = transliterator.transliterate(
                translation_text,
                target_language,
                client=client,
            )
            transliteration_text = translit_result.text

        # Tokenize
        trans_tokens = split_highlight_tokens(translation_text) if translation_text else []
        translit_tokens = split_highlight_tokens(transliteration_text) if transliteration_text else []

        result.update({
            "translation": translation_text,
            "transliteration": transliteration_text,
            "trans_tokens": trans_tokens,
            "translit_tokens": translit_tokens,
            "trans_count": len(trans_tokens),
            "translit_count": len(translit_tokens),
            "aligned": len(trans_tokens) == len(translit_tokens),
            "diff": len(trans_tokens) - len(translit_tokens),
        })

    except Exception as e:
        result["error"] = str(e)

    if verbose:
        status = "✓" if result["aligned"] else "✗"
        print(f"\n{status} {target_language.upper()}: {sentence[:50]}...")
        print(f"   Translation ({result['trans_count']}): {result['translation'][:60]}...")
        print(f"   Tokens: {result['trans_tokens']}")
        print(f"   Transliteration ({result['translit_count']}): {result['transliteration'][:60]}...")
        print(f"   Tokens: {result['translit_tokens']}")
        if not result["aligned"]:
            print(f"   ⚠ Token diff: {result['diff']}")
        if result["error"]:
            print(f"   ❌ Error: {result['error']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Test CJK tokenization alignment")
    parser.add_argument(
        "--languages",
        nargs="+",
        default=CJK_LANGUAGES,
        help="Languages to test",
    )
    parser.add_argument(
        "--sentence",
        action="append",
        dest="sentences",
        help="Custom sentence(s) to test",
    )
    parser.add_argument(
        "--report",
        type=str,
        help="Path to save JSON report",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity",
    )
    args = parser.parse_args()

    sentences = args.sentences if args.sentences else DEFAULT_SENTENCES[:3]
    verbose = not args.quiet

    print("=" * 60)
    print("CJK Tokenization Alignment Test")
    print("=" * 60)

    # Initialize client
    client = llm_client_manager.get_default_client()
    transliterator = get_transliterator()

    print(f"\nModel: {client.model}")
    print(f"Languages: {', '.join(args.languages)}")
    print(f"Sentences: {len(sentences)}")

    # Run tests
    results = {}
    for lang in args.languages:
        print(f"\n{'='*60}")
        print(f"Testing: {lang.upper()}")
        print("=" * 60)

        lang_results = []
        for sentence in sentences:
            result = test_translation(
                sentence,
                lang,
                client,
                transliterator,
                verbose=verbose,
            )
            lang_results.append(result)

        # Calculate summary
        total = len(lang_results)
        aligned = sum(1 for r in lang_results if r["aligned"])
        avg_diff = sum(abs(r["diff"]) for r in lang_results) / total if total else 0

        results[lang] = {
            "total": total,
            "aligned": aligned,
            "success_rate": aligned / total if total else 0,
            "avg_diff": avg_diff,
            "results": lang_results,
        }

        print(f"\n{lang} Summary:")
        print(f"   Success rate: {results[lang]['success_rate']:.1%}")
        print(f"   Aligned: {aligned}/{total}")
        print(f"   Avg token diff: {avg_diff:.2f}")

    # Overall summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)

    total_tests = sum(r["total"] for r in results.values())
    total_aligned = sum(r["aligned"] for r in results.values())
    overall_rate = total_aligned / total_tests if total_tests else 0

    print(f"Total tests: {total_tests}")
    print(f"Total aligned: {total_aligned}")
    print(f"Overall success rate: {overall_rate:.1%}")

    for lang, data in results.items():
        status = "✓" if data["success_rate"] >= 0.5 else "✗"
        print(f"   {status} {lang}: {data['success_rate']:.1%}")

    # Save report if requested
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print(f"\nReport saved to: {report_path}")

    # Exit with appropriate code
    sys.exit(0 if overall_rate >= 0.5 else 1)


if __name__ == "__main__":
    main()
