#!/usr/bin/env python3
"""
Test Piper voice speeds across all languages and calculate recommended speed multipliers.

This script:
1. Synthesizes a short test sentence in each language
2. Measures the audio duration and calculates speech rate (chars/sec)
3. Compares to English baseline to determine speed multipliers
4. Outputs recommended config updates
"""

import subprocess
import tempfile
import os
import sys
from pathlib import Path
from pydub import AudioSegment
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

PIPER_VOICES_DIR = "/Volumes/WD-1TB/ml-models/piper-voices"
PIPER_EXECUTABLE = "/Users/fifo/.pyenv/shims/piper"

# Test sentences - short phrases that are roughly equivalent in meaning
# Using common phrases that translate to similar lengths
TEST_SENTENCES = {
    "en": "Hello, how are you today? I hope you are doing well.",
    "ar": "مرحبا، كيف حالك اليوم؟ أتمنى أن تكون بخير.",
    "bg": "Здравей, как си днес? Надявам се да си добре.",
    "ca": "Hola, com estàs avui? Espero que estiguis bé.",
    "cs": "Ahoj, jak se máš dnes? Doufám, že se máš dobře.",
    "cy": "Helo, sut wyt ti heddiw? Gobeithio dy fod ti'n iawn.",
    "da": "Hej, hvordan har du det i dag? Jeg håber du har det godt.",
    "de": "Hallo, wie geht es dir heute? Ich hoffe, es geht dir gut.",
    "el": "Γεια σου, πώς είσαι σήμερα; Ελπίζω να είσαι καλά.",
    "es": "Hola, ¿cómo estás hoy? Espero que estés bien.",
    "fa": "سلام، امروز حالت چطوره؟ امیدوارم خوب باشی.",
    "fi": "Hei, mitä kuuluu tänään? Toivottavasti voit hyvin.",
    "fr": "Bonjour, comment allez-vous aujourd'hui? J'espère que vous allez bien.",
    "hi": "नमस्ते, आज आप कैसे हैं? मुझे आशा है कि आप ठीक हैं।",
    "hu": "Szia, hogy vagy ma? Remélem, jól vagy.",
    "id": "Halo, apa kabar hari ini? Semoga kamu baik-baik saja.",
    "is": "Halló, hvernig hefur þú það í dag? Ég vona að þér líði vel.",
    "it": "Ciao, come stai oggi? Spero che tu stia bene.",
    "ka": "გამარჯობა, როგორ ხარ დღეს? იმედი მაქვს კარგად ხარ.",
    "kk": "Сәлем, бүгін қалайсың? Сенің жақсы екеніңді үміттенемін.",
    "lb": "Moien, wéi geet et dir haut? Ech hoffen et geet dir gutt.",
    "lv": "Sveiki, kā jums šodien klājas? Ceru, ka jums viss kārtībā.",
    "ml": "ഹലോ, ഇന്ന് നിങ്ങൾക്ക് എങ്ങനെയുണ്ട്? നിങ്ങൾ സുഖമായിരിക്കുമെന്ന് പ്രതീക്ഷിക്കുന്നു.",
    "ne": "नमस्ते, आज तिमीलाई कस्तो छ? तिमी ठीक छौ भन्ने आशा गर्छु।",
    "nl": "Hallo, hoe gaat het vandaag? Ik hoop dat het goed met je gaat.",
    "no": "Hei, hvordan har du det i dag? Jeg håper du har det bra.",
    "pl": "Cześć, jak się masz dzisiaj? Mam nadzieję, że dobrze się czujesz.",
    "pt": "Olá, como você está hoje? Espero que esteja bem.",
    "ro": "Bună, ce mai faci azi? Sper că ești bine.",
    "ru": "Привет, как дела сегодня? Надеюсь, у тебя всё хорошо.",
    "sk": "Ahoj, ako sa máš dnes? Dúfam, že sa máš dobre.",
    "sl": "Živjo, kako si danes? Upam, da si v redu.",
    "sr": "Здраво, како си данас? Надам се да си добро.",
    "sv": "Hej, hur mår du idag? Jag hoppas att du mår bra.",
    "sw": "Habari, hali yako ikoje leo? Natumaini uko sawa.",
    "te": "హలో, ఈ రోజు మీకు ఎలా ఉంది? మీరు బాగున్నారని ఆశిస్తున్నాను.",
    "tr": "Merhaba, bugün nasılsın? Umarım iyisindir.",
    "uk": "Привіт, як справи сьогодні? Сподіваюсь, у тебе все добре.",
    "vi": "Xin chào, hôm nay bạn khỏe không? Tôi hy vọng bạn khỏe.",
    "zh": "你好，今天你好吗？希望你一切都好。",
}


def get_first_voice_for_lang(lang: str) -> str | None:
    """Get the first available voice for a language."""
    config_path = project_root / "config" / "piper_voices.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    voices = config.get("voices", {}).get(lang, [])
    for voice in voices:
        voice_path = Path(PIPER_VOICES_DIR) / f"{voice}.onnx"
        if voice_path.exists():
            return voice
    return None


def synthesize_and_measure(voice: str, text: str) -> tuple[float, int]:
    """
    Synthesize text with Piper and return (duration_seconds, char_count).
    """
    voice_path = Path(PIPER_VOICES_DIR) / f"{voice}.onnx"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output_path = f.name

    try:
        # Run piper
        process = subprocess.run(
            [
                PIPER_EXECUTABLE,
                "--model", str(voice_path),
                "--output_file", output_path,
            ],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )

        if process.returncode != 0:
            print(f"  Error: {process.stderr.decode()[:100]}")
            return 0.0, 0

        # Load and measure audio duration
        audio = AudioSegment.from_wav(output_path)
        duration = len(audio) / 1000.0  # Convert ms to seconds

        return duration, len(text)

    except Exception as e:
        print(f"  Exception: {e}")
        return 0.0, 0

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def main():
    print("=" * 70)
    print("Piper Voice Speed Test")
    print("=" * 70)
    print()

    results = {}

    # First, get English baseline
    en_voice = get_first_voice_for_lang("en")
    if not en_voice:
        print("ERROR: No English voice found!")
        return

    print(f"Testing English baseline with {en_voice}...")
    en_duration, en_chars = synthesize_and_measure(en_voice, TEST_SENTENCES["en"])
    if en_duration == 0:
        print("ERROR: Failed to synthesize English baseline!")
        return

    en_rate = en_chars / en_duration
    print(f"  Duration: {en_duration:.2f}s, Chars: {en_chars}, Rate: {en_rate:.2f} chars/sec")
    print()

    results["en"] = {
        "voice": en_voice,
        "duration": en_duration,
        "chars": en_chars,
        "rate": en_rate,
        "multiplier": 1.0,
    }

    # Test all other languages
    for lang, sentence in sorted(TEST_SENTENCES.items()):
        if lang == "en":
            continue

        voice = get_first_voice_for_lang(lang)
        if not voice:
            print(f"[{lang}] No voice found, skipping")
            continue

        print(f"[{lang}] Testing with {voice}...")
        duration, chars = synthesize_and_measure(voice, sentence)

        if duration == 0:
            print(f"  FAILED")
            continue

        rate = chars / duration
        # Calculate multiplier: if voice is slower (lower rate), multiplier > 1
        # We want to normalize to English rate
        multiplier = en_rate / rate if rate > 0 else 1.0

        print(f"  Duration: {duration:.2f}s, Chars: {chars}, Rate: {rate:.2f} chars/sec")
        print(f"  Relative to English: {multiplier:.2f}x {'(slower)' if multiplier > 1 else '(faster)'}")

        results[lang] = {
            "voice": voice,
            "duration": duration,
            "chars": chars,
            "rate": rate,
            "multiplier": round(multiplier, 1),
        }

    print()
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Lang':<6} {'Voice':<35} {'Rate':<10} {'Multiplier':<12} {'Action'}")
    print("-" * 70)

    # Sort by multiplier (slowest first)
    sorted_results = sorted(results.items(), key=lambda x: x[1]["multiplier"], reverse=True)

    for lang, data in sorted_results:
        rate_str = f"{data['rate']:.1f}"
        mult = data["multiplier"]

        # Determine if adjustment needed (threshold: >10% deviation)
        if mult > 1.1:
            action = f"Speed up to {mult:.1f}x"
        elif mult < 0.9:
            action = f"Slow down to {mult:.1f}x"
        else:
            action = "OK (close to baseline)"

        print(f"{lang:<6} {data['voice']:<35} {rate_str:<10} {mult:<12.1f} {action}")

    print()
    print("=" * 70)
    print("RECOMMENDED speed_multipliers CONFIG")
    print("=" * 70)
    print()
    print("speed_multipliers:")

    # Only output languages that need adjustment (>10% deviation)
    needs_adjustment = [(lang, data) for lang, data in sorted_results
                        if data["multiplier"] > 1.1 or data["multiplier"] < 0.9]

    for lang, data in sorted(needs_adjustment, key=lambda x: x[0]):
        mult = data["multiplier"]
        comment = "slower" if mult > 1 else "faster"
        print(f"  {lang}: {mult:.1f}    # {data['voice']} speaks {comment} than English")

    print()
    print("Languages close to English baseline (no multiplier needed):")
    close_to_baseline = [lang for lang, data in results.items()
                         if 0.9 <= data["multiplier"] <= 1.1]
    print(f"  {', '.join(sorted(close_to_baseline))}")


if __name__ == "__main__":
    main()
