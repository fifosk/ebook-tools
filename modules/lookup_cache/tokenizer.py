"""Word tokenization and normalization for lookup cache.

This module handles extracting and normalizing words from text,
with language-aware stopword filtering to reduce cache size.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Optional, Set

from .models import LookupCache

# Stopword sets for common languages
# These are high-frequency function words that typically don't need definition lookups

ENGLISH_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "as",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "must", "shall", "can", "need", "dare", "ought", "used", "to", "of",
    "in", "for", "on", "with", "at", "by", "from", "up", "about", "into",
    "over", "after", "beneath", "under", "above", "this", "that", "these",
    "those", "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves", "he", "him", "his",
    "himself", "she", "her", "hers", "herself", "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves", "what", "which", "who",
    "whom", "when", "where", "why", "how", "all", "each", "every", "both",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "than", "too", "very", "just", "also", "now",
    "here", "there", "out", "any", "much", "many", "even", "still", "yet",
}

ARABIC_STOPWORDS: Set[str] = {
    # Common particles and prepositions
    "في", "من", "إلى", "على", "عن", "مع", "بين", "حتى", "لكن", "أو",
    "و", "ف", "ثم", "أم", "لا", "ما", "إن", "أن", "كان", "كانت",
    # Pronouns and demonstratives
    "هو", "هي", "هم", "هن", "أنا", "نحن", "أنت", "أنتم", "أنتن",
    "هذا", "هذه", "ذلك", "تلك", "هؤلاء", "أولئك",
    # Common verbs
    "كان", "يكون", "كانت", "كانوا", "قد", "قال", "قالت",
    # Articles and conjunctions
    "ال", "الذي", "التي", "الذين", "اللواتي", "اللاتي",
    # Question words (often want definitions for learners, but skip basic ones)
    "هل",
}

GERMAN_STOPWORDS: Set[str] = {
    "der", "die", "das", "ein", "eine", "einer", "einem", "einen",
    "und", "oder", "aber", "wenn", "dann", "so", "als", "auch",
    "ist", "sind", "war", "waren", "sein", "haben", "hat", "hatte",
    "wird", "werden", "wurde", "wurden", "kann", "können", "konnte",
    "muss", "müssen", "musste", "soll", "sollte", "darf", "dürfte",
    "in", "an", "auf", "für", "mit", "bei", "nach", "von", "zu",
    "ich", "du", "er", "sie", "es", "wir", "ihr", "sie",
    "mein", "dein", "sein", "ihr", "unser", "euer",
    "dieser", "diese", "dieses", "jener", "jene", "jenes",
    "was", "wer", "wo", "wann", "wie", "warum",
    "nicht", "nur", "auch", "schon", "noch", "sehr", "mehr",
}

FRENCH_STOPWORDS: Set[str] = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d",
    "et", "ou", "mais", "donc", "car", "ni", "que", "qui",
    "est", "sont", "était", "étaient", "être", "avoir", "a", "ont",
    "sera", "serait", "peut", "peuvent", "doit", "doivent",
    "dans", "sur", "sous", "avec", "sans", "pour", "par", "en",
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "mon", "ton", "son", "ma", "ta", "sa", "mes", "tes", "ses",
    "ce", "cette", "ces", "cet", "celui", "celle", "ceux", "celles",
    "ne", "pas", "plus", "moins", "très", "aussi", "encore",
}

SPANISH_STOPWORDS: Set[str] = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "y", "o", "pero", "porque", "que", "quien", "cual",
    "es", "son", "era", "eran", "ser", "estar", "está", "están",
    "ha", "han", "había", "habían", "haber", "tener", "tiene", "tienen",
    "en", "de", "del", "al", "con", "sin", "por", "para", "sobre",
    "yo", "tú", "él", "ella", "nosotros", "vosotros", "ellos", "ellas",
    "mi", "tu", "su", "mis", "tus", "sus", "nuestro", "vuestro",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
    "no", "sí", "más", "menos", "muy", "también", "todavía",
}

ITALIAN_STOPWORDS: Set[str] = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
    "e", "o", "ma", "però", "perché", "che", "chi", "quale",
    "è", "sono", "era", "erano", "essere", "avere", "ha", "hanno",
    "sarà", "sarebbe", "può", "possono", "deve", "devono",
    "in", "di", "da", "a", "con", "su", "per", "tra", "fra",
    "io", "tu", "lui", "lei", "noi", "voi", "loro",
    "mio", "tuo", "suo", "mia", "tua", "sua", "nostro", "vostro",
    "questo", "questa", "questi", "queste", "quello", "quella",
    "non", "sì", "più", "meno", "molto", "anche", "ancora",
}

PORTUGUESE_STOPWORDS: Set[str] = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "e", "ou", "mas", "porém", "porque", "que", "quem", "qual",
    "é", "são", "era", "eram", "ser", "estar", "está", "estão",
    "tem", "têm", "tinha", "tinham", "ter", "haver", "há",
    "em", "de", "da", "do", "das", "dos", "com", "sem", "por", "para",
    "eu", "tu", "ele", "ela", "nós", "vós", "eles", "elas",
    "meu", "teu", "seu", "minha", "tua", "sua", "nosso", "vosso",
    "este", "esta", "estes", "estas", "esse", "essa", "esses", "essas",
    "não", "sim", "mais", "menos", "muito", "também", "ainda",
}

TURKISH_STOPWORDS: Set[str] = {
    "bir", "ve", "veya", "ama", "fakat", "çünkü", "için", "ile",
    "bu", "şu", "o", "bunlar", "şunlar", "onlar",
    "ben", "sen", "biz", "siz", "onlar",
    "benim", "senin", "onun", "bizim", "sizin", "onların",
    "var", "yok", "olan", "olmak", "oldu", "olur",
    "de", "da", "mi", "mı", "mu", "mü",
    "ne", "neden", "nasıl", "nerede", "ne zaman",
    "daha", "çok", "az", "en", "kadar",
}

HINDI_STOPWORDS: Set[str] = {
    "का", "की", "के", "को", "में", "से", "पर", "और", "या", "लेकिन",
    "यह", "वह", "ये", "वे", "इस", "उस", "इन", "उन",
    "मैं", "तुम", "आप", "हम", "वे",
    "है", "हैं", "था", "थे", "थी", "होना", "करना", "कर",
    "नहीं", "हाँ", "भी", "ही", "तो", "अब", "बहुत", "कुछ",
}

# Mapping from language names/codes to stopword sets
STOPWORD_SETS: dict[str, Set[str]] = {
    "english": ENGLISH_STOPWORDS,
    "en": ENGLISH_STOPWORDS,
    "arabic": ARABIC_STOPWORDS,
    "ar": ARABIC_STOPWORDS,
    "german": GERMAN_STOPWORDS,
    "de": GERMAN_STOPWORDS,
    "french": FRENCH_STOPWORDS,
    "fr": FRENCH_STOPWORDS,
    "spanish": SPANISH_STOPWORDS,
    "es": SPANISH_STOPWORDS,
    "italian": ITALIAN_STOPWORDS,
    "it": ITALIAN_STOPWORDS,
    "portuguese": PORTUGUESE_STOPWORDS,
    "pt": PORTUGUESE_STOPWORDS,
    "turkish": TURKISH_STOPWORDS,
    "tr": TURKISH_STOPWORDS,
    "hindi": HINDI_STOPWORDS,
    "hi": HINDI_STOPWORDS,
}

# Regex patterns for word extraction
# Matches word characters plus full Unicode block ranges for scripts with combining
# marks (vowel signs, virama, nukta, anusvara, etc.) that Python's \w misses.
# Without the full block ranges, Indic scripts like Devanagari get split at vowel
# sign boundaries (e.g., भाग → भ + ग) because \w excludes Mn/Mc categories.
WORD_PATTERN = re.compile(
    r"(?:"
    r"\w"                       # Word chars (letters, digits, underscore)
    r"|[\u0300-\u036F]"         # Combining Diacritical Marks
    r"|[\u0600-\u06FF]"         # Arabic
    r"|[\u0750-\u077F]"         # Arabic Supplement
    r"|[\u08A0-\u08FF]"         # Arabic Extended-A
    r"|[\u0900-\u097F]"         # Devanagari (full block incl. vowel signs)
    r"|[\u0980-\u09FF]"         # Bengali
    r"|[\u0A00-\u0A7F]"         # Gurmukhi
    r"|[\u0A80-\u0AFF]"         # Gujarati
    r"|[\u0B00-\u0B7F]"         # Oriya
    r"|[\u0B80-\u0BFF]"         # Tamil
    r"|[\u0C00-\u0C7F]"         # Telugu
    r"|[\u0C80-\u0CFF]"         # Kannada
    r"|[\u0D00-\u0D7F]"         # Malayalam
    r"|[\u0D80-\u0DFF]"         # Sinhala
    r"|[\u0E00-\u0E7F]"         # Thai
    r"|[\u0E80-\u0EFF]"         # Lao
    r"|[\u1000-\u109F]"         # Myanmar
    r"|[\uFB50-\uFDFF]"         # Arabic Presentation Forms-A
    r"|[\uFE70-\uFEFF]"         # Arabic Presentation Forms-B
    r")+",
    re.UNICODE,
)

# Pattern to detect if text contains Arabic script
ARABIC_SCRIPT_PATTERN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")

# Pattern to detect CJK characters (Chinese, Japanese, Korean)
CJK_PATTERN = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7AF]")


def normalize_word(word: str) -> str:
    """Normalize a word for cache lookup.

    Applies lowercase, Unicode normalization, strips whitespace/punctuation,
    and removes Arabic diacritics (tashkeel) for consistent matching.

    Args:
        word: Word to normalize.

    Returns:
        Normalized word form.
    """
    if not word:
        return ""

    # Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", word)

    # Remove Arabic diacritics (tashkeel/harakat): U+064B to U+065F
    # These include: fatha, damma, kasra, shadda, sukun, tanween, etc.
    normalized = re.sub(r"[\u064B-\u065F]", "", normalized)

    # Lowercase (works for most scripts)
    normalized = normalized.lower()

    # Strip leading/trailing whitespace and common punctuation
    normalized = normalized.strip()

    # Remove common punctuation at word boundaries
    # But preserve internal characters (e.g., hyphenated words)
    # Include various Unicode quotation marks
    punct_chars = ".,;:!?\"'()[]{}«»\u201E\u201C\u201F\u2018\u201A\u2019\u201B"
    normalized = normalized.strip(punct_chars)

    return normalized


def is_stopword(word: str, language: str) -> bool:
    """Check if a word is a stopword for the given language.

    Args:
        word: Word to check (should be normalized).
        language: Language name or code (e.g., 'Arabic', 'en').

    Returns:
        True if the word is a stopword, False otherwise.
    """
    if not word:
        return True

    # Normalize language key
    lang_key = language.lower().strip()

    # Look up stopword set
    stopwords = STOPWORD_SETS.get(lang_key, set())

    # Check if word is in stopword set
    if word in stopwords:
        return True

    # Fallback heuristic: very short words (1-2 chars) in Latin scripts
    # are often stopwords (articles, prepositions)
    if len(word) <= 2 and word.isascii():
        return True

    return False


def extract_words(text: str, language: str = "") -> List[str]:
    """Extract words from text.

    Handles various scripts including Arabic, Latin, and CJK.

    Args:
        text: Text to extract words from.
        language: Optional language hint for script-specific handling.

    Returns:
        List of extracted words (not normalized, not deduplicated).
    """
    if not text:
        return []

    # Check if text contains CJK characters
    if CJK_PATTERN.search(text):
        # CJK text: each character is typically a word
        # Extract CJK chars individually plus any non-CJK words
        words = []
        for char in text:
            if CJK_PATTERN.match(char):
                words.append(char)
        # Also extract any Latin/other words
        words.extend(WORD_PATTERN.findall(text))
        return words

    # For other scripts, use word pattern matching
    return WORD_PATTERN.findall(text)


def extract_unique_words(
    sentences: List[str],
    existing_cache: Optional[LookupCache] = None,
    *,
    language: str = "",
    skip_stopwords: bool = True,
    min_word_length: int = 2,
) -> List[str]:
    """Extract unique words from sentences, filtering out cached and stopwords.

    Args:
        sentences: List of sentences to extract words from.
        existing_cache: Optional cache to check for already-cached words.
        language: Language for stopword detection.
        skip_stopwords: Whether to filter out stopwords.
        min_word_length: Minimum word length to include.

    Returns:
        List of unique words not in cache and not stopwords.
    """
    seen: Set[str] = set()
    unique_words: List[str] = []

    for sentence in sentences:
        if not sentence:
            continue

        raw_words = extract_words(sentence, language)

        for raw_word in raw_words:
            normalized = normalize_word(raw_word)

            if not normalized:
                continue

            # Skip if too short
            if len(normalized) < min_word_length:
                continue

            # Skip if already seen in this batch
            if normalized in seen:
                continue

            # Skip if already in existing cache
            if existing_cache is not None and existing_cache.get(normalized):
                continue

            # Skip stopwords if requested
            if skip_stopwords and is_stopword(normalized, language):
                continue

            seen.add(normalized)
            unique_words.append(normalized)

    return unique_words


def count_skipped_stopwords(
    sentences: List[str],
    existing_cache: Optional[LookupCache] = None,
    *,
    language: str = "",
) -> int:
    """Count how many stopwords would be skipped from the sentences.

    Useful for statistics tracking.

    Args:
        sentences: List of sentences to analyze.
        existing_cache: Optional cache to check.
        language: Language for stopword detection.

    Returns:
        Number of unique stopwords that would be skipped.
    """
    seen: Set[str] = set()
    stopword_count = 0

    for sentence in sentences:
        if not sentence:
            continue

        raw_words = extract_words(sentence, language)

        for raw_word in raw_words:
            normalized = normalize_word(raw_word)

            if not normalized or normalized in seen:
                continue

            seen.add(normalized)

            if is_stopword(normalized, language):
                # Don't count if already cached
                if existing_cache is None or not existing_cache.get(normalized):
                    stopword_count += 1

    return stopword_count


__all__ = [
    "count_skipped_stopwords",
    "extract_unique_words",
    "extract_words",
    "is_stopword",
    "normalize_word",
]
