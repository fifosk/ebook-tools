#!/usr/bin/env python3
import os
import concurrent.futures
import sys, re, json, subprocess, requests, io, tempfile, warnings, statistics, math, urllib.parse, base64, time
from tqdm import tqdm
from ebooklib import epub
from bs4 import BeautifulSoup

# Suppress warnings from ebooklib
warnings.filterwarnings("ignore", category=UserWarning, module="ebooklib.epub")
warnings.filterwarnings("ignore", category=FutureWarning, module="ebooklib.epub")

# ReportLab imports for PDF generation
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

# Arabic/Hebrew processing
import arabic_reshaper
from bidi.algorithm import get_display

# Audio generation (gTTS and pydub)
from gtts import gTTS
from pydub import AudioSegment
# Explicitly set ffmpeg converter for pydub
AudioSegment.converter = "/opt/homebrew/bin/ffmpeg"

# Video generation using Pillow and ffmpeg
from PIL import Image, ImageDraw, ImageFont

# -----------------------------------------------------------------------------
# Global Directories
# -----------------------------------------------------------------------------
# Working directory for EPUB files and final outputs
DEFAULT_WORKING_DIR = "/Volumes/Data/Download/Subs"
if not os.path.exists(DEFAULT_WORKING_DIR):
    os.makedirs(DEFAULT_WORKING_DIR)
os.chdir(DEFAULT_WORKING_DIR)

# Final output (stitched block files) are written to the "ebook" subfolder in DEFAULT_WORKING_DIR.
EBOOK_DIR = os.path.join(DEFAULT_WORKING_DIR, "ebook")
if not os.path.exists(EBOOK_DIR):
    os.makedirs(EBOOK_DIR)

# Temporary files (including individual sentence MP4 files) are written to the script's own "tmp" subfolder.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(SCRIPT_DIR, "tmp")
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

# -----------------------
# Global Variables for Audio/Video Options
# -----------------------
SELECTED_VOICE = "gTTS"
DEFAULT_MODEL = "gemma2:27b"
OLLAMA_MODEL = DEFAULT_MODEL
DEBUG = False
MAX_WORDS = 18
EXTEND_SPLIT_WITH_COMMA_SEMICOLON = False
MACOS_READING_SPEED = 100
SYNC_RATIO = 0.9
# New global tempo variable; 1.0 means normal speed.
TEMPO = 1.0

OLLAMA_API_URL = "http://localhost:11434/api/chat"

AUDIO_MODE_DESC = {
    "1": "Only translated sentence",
    "2": "Sentence numbering + translated sentence",
    "3": "Full original format (numbering, original sentence, translated sentence)",
    "4": "Original sentence + translated sentence",
    "5": "Only Original sentence"
}

WRITTEN_MODE_DESC = {
    "1": "Only fluent translation",
    "2": "Sentence numbering + fluent translation",
    "3": "Full original format (numbering, original sentence, fluent translation)",
    "4": "Original sentence + fluent translation"
}

# -----------------------
# Function: Get a Default Unicode-capable Font Path
# -----------------------
def get_default_font_path():
    if sys.platform == "darwin":
        for path in ["/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                     "/System/Library/Fonts/Supplemental/AppleGothic.ttf"]:
            if os.path.exists(path):
                return path
    elif sys.platform == "win32":
        path = r"C:\Windows\Fonts\arialuni.ttf"
        if os.path.exists(path):
            return path
    else:
        for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                     "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]:
            if os.path.exists(path):
                return path
    return "Arial.ttf"

# -----------------------
# Colors for slide text
# -----------------------
original_sentence_color = (255, 255, 0)    # standard yellow
translation_color = (153, 255, 153)  # lighter, pastel green
transliteration_color = (255, 255, 0)  # light grey
highlight_color        = (255, 255, 204)    # light yellow for current word highlight (unchanged)

# -----------------------
# Updated TOP_LANGUAGES List (Added Persian)
# -----------------------
TOP_LANGUAGES = [
    "Afrikaans", "Albanian", "Arabic", "Armenian", "Basque", "Bengali", "Bosnian", "Burmese",
    "Catalan", "Chinese (Simplified)", "Chinese (Traditional)", "Czech", "Croatian", "Danish",
    "Dutch", "English", "Esperanto", "Estonian", "Filipino", "Finnish", "French", "German",
    "Greek", "Gujarati", "Hausa", "Hebrew", "Hindi", "Hungarian", "Icelandic", "Indonesian",
    "Italian", "Japanese", "Javanese", "Kannada", "Khmer", "Korean", "Latin", "Latvian",
    "Macedonian", "Malay", "Malayalam", "Marathi", "Nepali", "Norwegian", "Polish",
    "Portuguese", "Romanian", "Russian", "Sinhala", "Slovak", "Serbian", "Sundanese",
    "Swahili", "Swedish", "Tamil", "Telugu", "Thai", "Turkish", "Ukrainian", "Urdu",
    "Vietnamese", "Welsh", "Xhosa", "Yoruba", "Zulu", "Persian"
]

# -----------------------
# Global variable for non-Latin languages (Added Persian)
# -----------------------
NON_LATIN_LANGUAGES = {
    "Arabic", "Armenian", "Chinese (Simplified)", "Chinese (Traditional)",
    "Hebrew", "Japanese", "Korean", "Russian", "Thai", "Greek", "Hindi", "Bengali", "Tamil", "Telugu", "Gujarati", "Persian"
}

# -----------------------
# Global option: Word highlighting for video slides (default enabled)
# -----------------------
WORD_HIGHLIGHTING = True

# -----------------------
# Helper Function: Change Audio Tempo
# -----------------------
def change_audio_tempo(sound, tempo=1.0):
    """
    Adjusts the tempo of an AudioSegment by modifying its frame_rate.
    (Note: This method also changes the pitch.)
    """
    if tempo == 1.0:
        return sound
    new_frame_rate = int(sound.frame_rate * tempo)
    return sound._spawn(sound.raw_data, overrides={'frame_rate': new_frame_rate}).set_frame_rate(sound.frame_rate)

# -----------------------
# Function: Print Languages in Four Columns
# -----------------------
def print_languages_in_four_columns():
    languages = TOP_LANGUAGES[:]
    n = len(languages)
    cols = 4
    rows = math.ceil(n / cols)
    col_width = max(len(s) for s in languages) + 4
    for r in range(rows):
        row_items = []
        for c in range(cols):
            idx = r + c * rows
            if idx < n:
                row_items.append(f"{idx+1:2d}. {languages[idx]:<{col_width}}")
        print("".join(row_items))

# -----------------------
# Helper Functions for Text Wrapping & Font Adjustment
# -----------------------
def wrap_text(text, draw, font, max_width):
    if " " in text:
        words = text.split()
        if not words:
            return ""
        lines = []
        current_line = words[0]
        for word in words[1:]:
            test_line = current_line + " " + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return "\n".join(lines)
    else:
        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
        return "\n".join(lines)

def adjust_font_and_wrap_text(text, draw, slide_size, initial_font_size, font_path="Arial.ttf",
                              max_width_fraction=0.9, max_height_fraction=0.9):
    max_width = slide_size[0] * max_width_fraction
    max_height = slide_size[1] * max_height_fraction
    font_size = int(initial_font_size * 0.85)  # Reduce font size by 15%
    while font_size > 10:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            font = ImageFont.load_default()
        wrapped_text = wrap_text(text, draw, font, max_width)
        total_height = sum((draw.textbbox((0, 0), line, font=font)[3] - 
                            draw.textbbox((0, 0), line, font=font)[1])
                           for line in wrapped_text.split("\n"))
        if total_height <= max_height:
            return wrapped_text, font
        font_size -= 2
    return wrapped_text, font

def adjust_font_for_three_segments(seg1, seg2, seg3, draw, slide_size, initial_font_size, font_path="Arial.ttf",
                                   max_width_fraction=0.9, max_height_fraction=0.9, spacing=10):
    max_width = slide_size[0] * max_width_fraction
    max_height = slide_size[1] * max_height_fraction
    font_size = int(initial_font_size * 0.25)
    while font_size > 10:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            font = ImageFont.load_default()
        wrapped1 = wrap_text(seg1, draw, font, max_width)
        wrapped2 = wrap_text(seg2, draw, font, max_width)
        wrapped3 = wrap_text(seg3, draw, font, max_width)
        total_height = 0
        for wrapped in (wrapped1, wrapped2, wrapped3):
            for line in wrapped.split("\n"):
                total_height += (draw.textbbox((0, 0), line, font=font)[3] - 
                                 draw.textbbox((0, 0), line, font=font)[1])
        total_height += 2 * spacing
        if total_height <= max_height:
            return wrapped1, wrapped2, wrapped3, font
        font_size -= 2
    return wrapped1, wrapped2, wrapped3, font

# -----------------------
# Global Configuration (Consolidated language codes)
# -----------------------
LANGUAGE_CODES = {
    "Afrikaans": "af",
    "Albanian": "sq",
    "Arabic": "ar",
    "Armenian": "hy",
    "Basque": "eu",
    "Bengali": "bn",
    "Bosnian": "bs",
    "Burmese": "my",
    "Catalan": "ca",
    "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW",
    "Czech": "cs",
    "Croatian": "hr",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Esperanto": "eo",
    "Estonian": "et",
    "Filipino": "tl",
    "Finnish": "fi",
    "French": "fr",
    "German": "de",
    "Greek": "el",
    "Gujarati": "gu",
    "Hausa": "ha",
    "Hebrew": "he",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Icelandic": "is",
    "Indonesian": "id",
    "Italian": "it",
    "Japanese": "ja",
    "Javanese": "jw",
    "Kannada": "kn",
    "Khmer": "km",
    "Korean": "ko",
    "Latin": "la",
    "Latvian": "lv",
    "Macedonian": "mk",
    "Malay": "ms",
    "Malayalam": "ml",
    "Marathi": "mr",
    "Nepali": "ne",
    "Norwegian": "no",
    "Polish": "pl",
    "Portuguese": "pt",
    "Romanian": "ro",
    "Russian": "ru",
    "Sinhala": "si",
    "Slovak": "sk",
    "Serbian": "sr",
    "Sundanese": "su",
    "Swahili": "sw",
    "Swedish": "sv",
    "Tamil": "ta",
    "Telugu": "te",
    "Thai": "th",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Urdu": "ur",
    "Vietnamese": "vi",
    "Welsh": "cy",
    "Xhosa": "xh",
    "Yoruba": "yo",
    "Zulu": "zu",
    "Persian": "fa"
}

# Use "gTTS" as the default voice selection.
SELECTED_VOICE = "gTTS"
DEFAULT_MODEL = "gemma2:27b"
OLLAMA_MODEL = DEFAULT_MODEL
DEBUG = False

MAX_WORDS = 18
EXTEND_SPLIT_WITH_COMMA_SEMICOLON = False

MACOS_READING_SPEED = 100

SYNC_RATIO = 0.9

OLLAMA_API_URL = "http://localhost:11434/api/chat"

AUDIO_MODE_DESC = {
    "1": "Only translated sentence",
    "2": "Sentence numbering + translated sentence",
    "3": "Full original format (numbering, original sentence, translated sentence)",
    "4": "Original sentence + translated sentence"
}

WRITTEN_MODE_DESC = {
    "1": "Only fluent translation",
    "2": "Sentence numbering + fluent translation",
    "3": "Full original format (numbering, original sentence, fluent translation)",
    "4": "Original sentence + fluent translation"
}

# -----------------------
# New Function: Fetch Book Cover from OpenLibrary
# -----------------------
def fetch_book_cover(query):
    q = urllib.parse.quote(query)
    url = f"http://openlibrary.org/search.json?title={q}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            docs = data.get("docs", [])
            for doc in docs:
                if "cover_i" in doc:
                    cover_id = doc["cover_i"]
                    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
                    cover_response = requests.get(cover_url, stream=True, timeout=10)
                    if cover_response.status_code == 200:
                        cover_img = Image.open(io.BytesIO(cover_response.content))
                        return cover_img
        return None
    except Exception as e:
        if DEBUG:
            print("Error fetching book cover:", e)
        return None

# -----------------------
# New Function: Update Book Cover File in Config
# -----------------------
def update_book_cover_file_in_config(config):
    title = config.get("book_title", "Unknown Title")
    author = config.get("book_author", "Unknown Author")
    default_cover_path = os.path.join(DEFAULT_WORKING_DIR, "book_cover.jpg")
    cover_file = config.get("book_cover_file")
    # If a cover file is already set and exists, use it.
    if cover_file and os.path.exists(cover_file):
        return config
    # Otherwise, check if the default cover exists in WORKING_DIR.
    if os.path.exists(default_cover_path):
        config["book_cover_file"] = default_cover_path
        config["book_cover_title"] = title
    else:
        cover_img = fetch_book_cover(f"{title} {author}")
        if cover_img:
            cover_img.thumbnail((80, 80))
            cover_img.save(default_cover_path, format="JPEG")
            config["book_cover_file"] = default_cover_path
            config["book_cover_title"] = title
        else:
            config["book_cover_file"] = None
    return config

# -----------------------
# Utility Functions (Text Processing, File Generation, etc.)
# -----------------------
def remove_quotes(text):
    for quote in ["“", "”", "‘", "’"]:
        text = text.replace(quote, "")
    return text

def extract_text_from_epub(epub_file):
    try:
        book = epub.read_epub(epub_file)
    except Exception as e:
        print(f"Error reading EPUB file '{epub_file}': {e}")
        sys.exit(1)
    text_content = ""
    for item in book.get_items():
        if isinstance(item, epub.EpubHtml):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text_content += soup.get_text(separator=" ", strip=True) + "\n"
    return text_content

def split_text_into_sentences_no_refine(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'([.?!])["\']\s+', r'\1 ', text)
    pattern = re.compile(
        r'(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)(?<!Dr\.)(?<!Jr\.)(?<!Sr\.)'
        r'(?<!Prof\.)(?<!St\.)(?<!e\.g\.)(?<!i\.e\.)(?<!vs\.)(?<!etc\.)'
        r'(?<=[.?!])\s+(?=[A-Z“])'
    )
    sentences = [s.strip() for s in pattern.split(text) if s.strip()]
    if EXTEND_SPLIT_WITH_COMMA_SEMICOLON:
        new_sentences = []
        for s in sentences:
            parts = re.split(r"[;,]\s*", s)
            new_sentences.extend([p.strip() for p in parts if p.strip()])
        return new_sentences
    return sentences

def refine_and_split_sentence(sentence, max_words):
    segments = []
    pattern_brackets = re.compile(r"\([^)]*\)")
    pos = 0
    for m in pattern_brackets.finditer(sentence):
        before = sentence[pos:m.start()].strip()
        if before:
            segments.append(before)
        bracket_text = m.group().strip("()").strip()
        if bracket_text:
            segments.append(bracket_text)
        pos = m.end()
    remainder = sentence[pos:].strip()
    if remainder:
        segments.append(remainder)
    if not segments:
        segments = [sentence]
    refined_segments = []
    pattern_quotes = re.compile(r'"([^"]+)"')
    for seg in segments:
        pos = 0
        parts = []
        for m in pattern_quotes.finditer(seg):
            before = seg[pos:m.start()].strip()
            if before:
                parts.append(before)
            quote_text = m.group(1).strip()
            if quote_text:
                parts.append(quote_text)
            pos = m.end()
        remainder = seg[pos:].strip()
        if remainder:
            parts.append(remainder)
        if parts:
            refined_segments.extend(parts)
        else:
            refined_segments.append(seg)
    final_segments = []
    for seg in refined_segments:
        if seg.startswith("- "):
            final_segments.append(seg[2:].strip())
        else:
            final_segments.append(seg)
    if EXTEND_SPLIT_WITH_COMMA_SEMICOLON:
        extended = []
        for seg in final_segments:
            parts = re.split(r"[;,]\s*", seg)
            extended.extend([p.strip() for p in parts if p.strip()])
        final_segments = extended
    final_sentences = []
    for seg in final_segments:
        words = seg.split()
        if len(words) > max_words:
            for i in range(0, len(words), max_words):
                final_sentences.append(" ".join(words[i:i+max_words]))
        else:
            final_sentences.append(seg)
    return final_sentences

def merge_single_char_sentences(sentences):
    if not sentences:
        return sentences
    merged = [sentences[0]]
    for sentence in sentences[1:]:
        if len(sentence.strip()) == 1:
            merged[-1] = merged[-1] + " " + sentence
        else:
            merged.append(sentence)
    return merged

def split_text_into_sentences(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'([.?!])["\']\s+', r'\1 ', text)
    pattern = re.compile(
        r'(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)(?<!Dr\.)(?<!Jr\.)(?<!Sr\.)'
        r'(?<!Prof\.)(?<!St\.)(?<!e\.g\.)(?<!i\.e\.)(?<!vs\.)(?<!etc\.)'
        r'(?<=[.?!])\s+(?=[A-Z“])'
    )
    raw = pattern.split(text)
    final = []
    for sentence in raw:
        sentence = sentence.replace("\n", " ").strip()
        if not sentence:
            continue
        if (sentence.startswith('"') and sentence.endswith('"')) or (sentence.startswith("“") and sentence.endswith("”")):
            final.append(sentence)
        else:
            refined = refine_and_split_sentence(sentence, max_words=MAX_WORDS)
            final.extend(refined)
    final = merge_single_char_sentences(final)
    return final

def update_sentence_config(config, refined_list):
    config["refined_list"] = refined_list
    if config.get("start_sentence_lookup"):
        query = config["start_sentence_lookup"].strip()
        found = None
        for idx, s in enumerate(refined_list):
            if query.lower() in s.lower():
                found = idx
                break
        if found is not None:
            config["start_sentence"] = found + 1
            print(f"(Lookup) Starting sentence updated to {config['start_sentence']} based on query '{query}'.")
        else:
            config["start_sentence"] = 1
            print(f"(Lookup) Query '{query}' not found. Starting sentence set to 1.")
        config["start_sentence_lookup"] = ""
    else:
        try:
            config["start_sentence"] = int(config.get("start_sentence", 1))
        except:
            config["start_sentence"] = 1
    return config

# -----------------------
# New Function: Get macOS Voices (Enhanced/Premium only)
# -----------------------
def get_macOS_voices():
    try:
        output = subprocess.check_output(["say", "-v", "?"], universal_newlines=True)
    except Exception as e:
        if DEBUG:
            print("Error retrieving macOS voices:", e)
        return []
    voices = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("#")
        details = parts[0].strip().split()
        if len(details) >= 3 and details[1].startswith("("):
            voice_name = details[0]
            quality = details[1].strip("()")
            locale = details[2]
        elif len(details) >= 2:
            voice_name = details[0]
            locale = details[1]
            quality = ""
        else:
            continue
        if quality in ["Enhanced", "Premium"]:
            voices.append(f"{voice_name} - {locale} - ({quality})")
    return voices

# -----------------------
# Audio Generation Functions
# -----------------------
def generate_macos_tts_audio(text, voice, lang_code):
    with tempfile.NamedTemporaryFile(suffix=".aiff", dir=TMP_DIR, delete=False) as tmp:
        tmp_filename = tmp.name
    try:
        cmd = ["say", "-v", voice, "-r", str(MACOS_READING_SPEED), "-o", tmp_filename, text]
        subprocess.run(cmd, check=True)
        audio = AudioSegment.from_file(tmp_filename, format="aiff")
    except subprocess.CalledProcessError as e:
        print(f"MacOS TTS command failed for voice '{voice}'. Falling back to default gTTS voice.", flush=True)
        tts = gTTS(text=text, lang=lang_code)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        audio = AudioSegment.from_file(fp, format="mp3")
    finally:
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)
    return audio

def generate_audio_segment(text, lang_code):
    global SELECTED_VOICE
    if SELECTED_VOICE == "gTTS":
        tts = gTTS(text=text, lang=lang_code)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return AudioSegment.from_file(fp, format="mp3")
    else:
        parts = SELECTED_VOICE.split(" - ")
        if len(parts) >= 2:
            voice_name = parts[0].strip()
            voice_locale = parts[1].strip()
        else:
            voice_name = SELECTED_VOICE
            voice_locale = ""
        if voice_locale.lower().startswith(lang_code.lower()):
            return generate_macos_tts_audio(text, voice_name, lang_code)
        else:
            tts = gTTS(text=text, lang=lang_code)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return AudioSegment.from_file(fp, format="mp3")

def generate_audio_for_sentence(sentence_number, input_sentence, fluent_translation, input_language, target_language, audio_mode, total_sentences):
    silence = AudioSegment.silent(duration=100)
    if audio_mode == "1":
        audio_translation = generate_audio_segment(fluent_translation, LANGUAGE_CODES.get(target_language, "en"))
        audio = audio_translation + silence
    elif audio_mode == "2":
        numbering_str = f"{sentence_number} - {(sentence_number/total_sentences * 100):.2f}%"
        audio_number = generate_audio_segment(numbering_str, "en")
        audio_translation = generate_audio_segment(fluent_translation, LANGUAGE_CODES.get(target_language, "en"))
        audio = audio_number + silence + audio_translation + silence
    elif audio_mode == "3":
        numbering_str = f"{sentence_number} - {(sentence_number/total_sentences * 100):.2f}%"
        audio_number = generate_audio_segment(numbering_str, "en")
        audio_input = generate_audio_segment(input_sentence, LANGUAGE_CODES.get(input_language, "en"))
        audio_translation = generate_audio_segment(fluent_translation, LANGUAGE_CODES.get(target_language, "en"))
        audio = audio_number + silence + audio_input + silence + audio_translation + silence
    elif audio_mode == "4":
        audio_original = generate_audio_segment(input_sentence, LANGUAGE_CODES.get(input_language, "en"))
        audio_translation = generate_audio_segment(fluent_translation, LANGUAGE_CODES.get(target_language, "en"))
        audio = audio_original + silence + audio_translation + silence
    elif audio_mode == "5":
        audio_original = generate_audio_segment(input_sentence, LANGUAGE_CODES.get(input_language, "en"))
        audio = audio_original + silence
    else:
        # Fallback to mode 4 behavior
        audio_original = generate_audio_segment(input_sentence, LANGUAGE_CODES.get(input_language, "en"))
        audio_translation = generate_audio_segment(fluent_translation, LANGUAGE_CODES.get(target_language, "en"))
        audio = audio_original + silence + audio_translation + silence
    global TEMPO
    audio = change_audio_tempo(audio, TEMPO)
    return audio

def write_html_file(filename, content_list):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("<html>\n<head>\n<meta charset='utf-8'>\n<title>Translation Output</title>\n</head>\n<body>\n")
            for block in content_list:
                f.write(f"<p>{block.replace(chr(10), '<br>')}</p>\n")
            f.write("</body>\n</html>")
    except Exception as e:
        if DEBUG:
            print(f"Error writing HTML file '{filename}': {e}")

def write_pdf_file(filename, content_list, target_language):
    try:
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase import pdfmetrics
        font_path = None
        if sys.platform == "darwin":
            font_path = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
        else:
            for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arialuni.ttf"]:
                if os.path.exists(path):
                    font_path = path
                    break
        if font_path and os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("UnicodeFont", font_path))
            pdfmetrics.registerFontFamily("UnicodeFont", normal="UnicodeFont")
        else:
            if DEBUG:
                print("Warning: Unicode font file not found; PDF output may not render non-Latin characters correctly.")
            pdfmetrics.registerFont(TTFont("UnicodeFont", "Helvetica"))
            pdfmetrics.registerFontFamily("UnicodeFont", normal="UnicodeFont")
        styles = getSampleStyleSheet()
        styles["Normal"].fontName = "UnicodeFont"
        doc = SimpleDocTemplate(filename, pagesize=letter)
        Story = []
        for block in content_list:
            Story.append(Paragraph(block.replace(chr(10), "<br>"), styles["Normal"]))
            Story.append(Spacer(1, 12))
        doc.build(Story)
    except Exception as e:
        if DEBUG:
            print(f"Error writing PDF file '{filename}': {e}")

def write_epub_file(filename, content_list, book_title):
    try:
        book = epub.EpubBook()
        book.set_identifier("id123456")
        book.set_title(book_title)
        book.set_language("en")
        book.add_author("Translation Bot")
        chapter = epub.EpubHtml(title="Full Translation", file_name="full.xhtml", lang="en")
        chapter_content = "<html><head><meta charset='utf-8'/></head><body>\n"
        for block in content_list:
            chapter_content += f"<p>{block.replace(chr(10), '<br>')}</p>\n"
        chapter_content += "</body></html>"
        chapter.content = chapter_content
        book.add_item(chapter)
        book.toc = (epub.Link("full.xhtml", "Full Translation", "full"),)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", chapter]
        epub.write_epub(filename, book)
    except Exception as e:
        if DEBUG:
            print(f"Error writing EPUB file '{filename}': {e}")

# -----------------------
# Modified Function: Combined Translation
# -----------------------
def translate_sentence_simple(sentence, input_language, target_language, include_transliteration=False):
    # Wrap the sentence to make it clear what should be translated
    wrapped_sentence = f"<<<{sentence}>>>"
    
    prompt = (
        f"Translate the following text from {input_language} to {target_language}.\n"
        "The text to be translated is enclosed between <<< and >>>.\n"
        "Provide ONLY the translated text on a SINGLE LINE , without any extra commentary or markers."
    )
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": wrapped_sentence}
        ],
        "stream": False
    }
    
    for attempt in range(3):
        try:
            if DEBUG:
                print(f"Sending translation request (attempt {attempt + 1})...")
                print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
                
            response = requests.post(OLLAMA_API_URL, json=payload)
            if response.status_code == 200:
                result = response.json().get("message", {}).get("content", "").strip()
                # Check for error responses indicating a missing text prompt or an incorrect translation response
                if ("please provide the text" in result.lower()) or ("في ترجمته إلى العربية" in result):
                    if DEBUG:
                        print("Received an error prompt response. Retrying...")
                    continue  # Retry if error found
                return result
            else:
                if DEBUG:
                    print(f"Translation error: {response.status_code} - {response.text}")
        except Exception as e:
            if DEBUG:
                print(f"Exception during translation: {e}")
    return "N/A"

def transliterate_sentence(translated_sentence, target_language):
    """
    Transliterate the given translated_sentence into a romanized form suitable for English pronunciation,
    using dedicated non-LLM packages for specific languages.
    """
    lang = target_language.lower()
    try:
        if lang == "arabic":
            from camel_tools.transliteration import Transliterator
            transliterator = Transliterator("buckwalter")
            return transliterator.transliterate(translated_sentence)
        elif lang == "chinese":
            import pypinyin
            # Convert Chinese characters to pinyin (without tone marks)
            pinyin_list = pypinyin.lazy_pinyin(translated_sentence)
            return " ".join(pinyin_list)
        elif lang == "japanese":
            import pykakasi
            kks = pykakasi.kakasi()
            result = kks.convert(translated_sentence)
            # Join the romanized output (Hepburn style)
            return " ".join(item['hepburn'] for item in result)
#        elif lang == "hindi":
#            from indic_transliteration.sanscript import transliterate, DEVANAGARI, ITRANS
#            # Convert from Devanagari to ITRANS (you can change ITRANS to any other supported scheme)
#            return transliterate(translated_sentence, DEVANAGARI, ITRANS)
#        elif lang == "hebrew":
#            # Using Unidecode as a basic transliteration tool for Hebrew.
#            from unidecode import unidecode
#            return unidecode(translated_sentence)
    except Exception as e:
        if DEBUG:
            print(f"Non-LLM transliteration error for {target_language}: {e}")
    # Fallback to LLM prompt if the dedicated package fails or if the language is not covered.
    prompt = (
        f"Transliterate the following sentence in {target_language} for English pronounciation.\n"
        "Provide ONLY the transliteration on a SINGLE LINE without ANY additional text or commentary."
    )
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": translated_sentence}
        ],
        "stream": False
    }
    try:
        if DEBUG:
            print("Sending transliteration request via LLM fallback...")
            print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        response = requests.post(OLLAMA_API_URL, json=payload)
        if response.status_code == 200:
            result = response.json().get("message", {}).get("content", "")
            return result.strip()
        else:
            if DEBUG:
                print(f"LLM fallback transliteration error: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        if DEBUG:
            print(f"Exception during LLM fallback transliteration: {e}")
        return ""

# -----------------------
# NEW: Helper Function to Generate a Sentence Slide Image
# -----------------------
from PIL import Image, ImageDraw, ImageFont

def generate_sentence_slide_image(block,
                                              original_highlight_word_index=None,
                                              translation_highlight_word_index=None,
                                              transliteration_highlight_word_index=None,
                                              slide_size=(1280, 720),
                                              initial_font_size=50,
                                              default_font_path="Arial.ttf",
                                              bg_color=(0, 0, 0),
                                              cover_img=None,
                                              header_info=""):
    """
    Draws a slide image for a sentence block with a multi-line header,
    adjusted for an audiobook-style cover display.
    
    The block should contain multiple lines:
      - The first line is used as header information (or replaced by header_info if provided).
      - The remaining lines are expected to contain:
          • The original sentence,
          • The translation,
          • (Optionally) the transliteration.
    
    Progressive Highlighting:
      - Original text: words with index < original_highlight_word_index are drawn in a highlight color.
      - Translation text:
          • For Chinese/Japanese: characters with index < translation_highlight_word_index are highlighted.
          • For other languages: words with index < translation_highlight_word_index are highlighted.
      - Transliteration text: words with index < transliteration_highlight_word_index are drawn in a highlight color.
    
    A thin separator line is drawn between segments for better visual delimitation.
    If a book cover image is provided, it is pasted as a larger thumbnail on the left side of the header.
    """
    from PIL import Image, ImageDraw, ImageFont
    
    # Create base image and drawing context
    img = Image.new("RGB", slide_size, bg_color)
    draw = ImageDraw.Draw(img)
    
    # Adjusted header height for audiobook style
    header_height = 150
    left_area_width = header_height  # reserved area for the cover thumbnail

    # Use header_info if provided; otherwise, take the first line of the block
    raw_lines = block.split("\n")
    header_line = raw_lines[0] if raw_lines else ""
    header_text = header_info if header_info else header_line

    # Draw header background
    draw.rectangle([0, 0, slide_size[0], header_height], fill=bg_color)

    # Paste cover image if available with larger dimensions (approx. 130x130 pixels)
    if cover_img:
        cover_thumb = cover_img.copy()
        new_width = left_area_width - 20  # e.g., 150 - 20 = 130 pixels
        new_height = header_height - 20     # e.g., 130 pixels
        cover_thumb.thumbnail((new_width, new_height))
        img.paste(cover_thumb, (10, (header_height - cover_thumb.height) // 2))

    # Load header font
    try:
        header_font = ImageFont.truetype(default_font_path, 24)
    except IOError:
        header_font = ImageFont.load_default()

    # Calculate header text dimensions to center it in the remaining space
    header_lines = header_text.split("\n")
    header_line_spacing = 4
    max_header_width = 0
    total_header_height = 0
    for line in header_lines:
        bbox = draw.textbbox((0, 0), line, font=header_font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        max_header_width = max(max_header_width, line_width)
        total_header_height += line_height
    total_header_height += header_line_spacing * (len(header_lines) - 1)
    if cover_img:
        available_width = slide_size[0] - left_area_width
        header_x = left_area_width + (available_width - max_header_width) // 2
    else:
        header_x = (slide_size[0] - max_header_width) // 2
    header_y = (header_height - total_header_height) // 2

    # Draw header text
    draw.multiline_text((header_x, header_y), header_text,
                        font=header_font,
                        fill=(255, 255, 255),
                        spacing=header_line_spacing,
                        align="center")

    # --- Active Text Section: Centering & Spacing Adjustments ---
    extra_line_spacing = 10   # extra pixels between wrapped lines
    segment_spacing = 20      # extra spacing between segments
    separator_pre_margin = 10 # extra space before drawing the separator line

    # Separator settings
    separator_color = (150, 150, 150)
    separator_thickness = 2
    separator_margin = 40

    # Extract content segments (skip header)
    content = "\n".join(raw_lines[1:]).strip()
    content_lines = [line.strip() for line in content.split("\n") if line.strip()]
    if len(content_lines) >= 3:
        original_seg = content_lines[0]
        translation_seg = content_lines[1]
        transliteration_seg = content_lines[2]
    elif len(content_lines) >= 2:
        original_seg = content_lines[0]
        translation_seg = " ".join(content_lines[1:])
        transliteration_seg = ""
    else:
        original_seg = translation_seg = content
        transliteration_seg = ""

    # Minimal text wrapping helper
    def wrap_text(text, draw, font, max_width):
        if " " not in text:
            lines_ = []
            current_line = ""
            for ch in text:
                test_line = current_line + ch
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines_.append(current_line)
                    current_line = ch
            if current_line:
                lines_.append(current_line)
            return "\n".join(lines_)
        else:
            words = text.split()
            lines_ = []
            current_line = words[0]
            for word in words[1:]:
                test_line = current_line + " " + word
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] <= max_width:
                    current_line = test_line
                else:
                    lines_.append(current_line)
                    current_line = word
            lines_.append(current_line)
            return "\n".join(lines_)

    def get_wrapped_text_and_font(text, draw, slide_size, initial_font_size, font_path):
        max_width = slide_size[0] * 0.9
        max_height = slide_size[1] * 0.9
        font_size = int(initial_font_size * 0.85)
        chosen_font = None
        wrapped_text = text
        while font_size > 10:
            try:
                test_font = ImageFont.truetype(font_path, font_size)
            except IOError:
                test_font = ImageFont.load_default()
            candidate_wrapped = wrap_text(text, draw, test_font, max_width)
            total_height = 0
            lines = candidate_wrapped.split("\n")
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=test_font)
                total_height += (bbox[3] - bbox[1])
                if i < len(lines) - 1:
                    total_height += extra_line_spacing
            if total_height <= max_height:
                wrapped_text = candidate_wrapped
                chosen_font = test_font
                break
            font_size -= 2
        if chosen_font is None:
            chosen_font = ImageFont.load_default()
        return wrapped_text, chosen_font

    # Wrap segments and calculate heights
    wrapped_orig, font_orig = get_wrapped_text_and_font(original_seg, draw, slide_size, initial_font_size, default_font_path)
    orig_lines = wrapped_orig.split("\n")
    def compute_height(lines, font):
        total = 0
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            total += (bbox[3] - bbox[1])
            if i < len(lines) - 1:
                total += extra_line_spacing
        return total
    orig_height = compute_height(orig_lines, font_orig)

    wrapped_trans, font_trans = get_wrapped_text_and_font(translation_seg, draw, slide_size, initial_font_size, default_font_path)
    trans_lines = wrapped_trans.split("\n")
    trans_height = compute_height(trans_lines, font_trans)

    translit_lines = []
    translit_height = 0
    if transliteration_seg:
        wrapped_translit, font_translit = get_wrapped_text_and_font(transliteration_seg, draw, slide_size, initial_font_size, default_font_path)
        translit_lines = wrapped_translit.split("\n")
        translit_height = compute_height(translit_lines, font_translit)

    # Total active text height including separators
    segments_heights = [orig_height, trans_height]
    if transliteration_seg:
        segments_heights.append(translit_height)
    num_segments = len(segments_heights)
    num_separators = num_segments - 1
    total_text_height_active = sum(segments_heights) + segment_spacing * num_separators + separator_thickness * num_separators

    # Center active text vertically in the remaining area below header
    available_area = slide_size[1] - header_height
    y_text = header_height + (available_area - total_text_height_active) // 2

    # --- Colors & Highlight Config ---
    global original_sentence_color, translation_color, transliteration_color
    original_sentence_color = (255, 255, 0)    # yellow
    translation_color = (153, 255, 153)          # pastel green
    transliteration_color = (255, 255, 0)      # light grey
    highlight_color = (255, 165, 0)              # bright orange
    scale_factor = 1.05

    # --- Draw Original Segment with Progressive Highlighting ---
    word_counter = 0
    orig_index_limit = original_highlight_word_index if original_highlight_word_index is not None else 0
    for line in orig_lines:
        words_line = line.split()
        space_bbox = draw.textbbox((0, 0), " ", font=font_orig)
        space_width = space_bbox[2] - space_bbox[0]
        total_width = sum((draw.textbbox((0, 0), w, font=font_orig)[2] - draw.textbbox((0, 0), w, font=font_orig)[0])
                          for w in words_line) + space_width * (len(words_line) - 1)
        x_line = (slide_size[0] - total_width) // 2
        for w in words_line:
            if word_counter < orig_index_limit:
                try:
                    highlight_font = ImageFont.truetype(default_font_path, int(font_orig.size * scale_factor))
                except IOError:
                    highlight_font = font_orig
                draw.text((x_line, y_text), w, font=highlight_font, fill=highlight_color)
            else:
                draw.text((x_line, y_text), w, font=font_orig, fill=original_sentence_color)
            w_bbox = draw.textbbox((0, 0), w, font=font_orig)
            w_width = w_bbox[2] - w_bbox[0]
            x_line += w_width + space_width
            word_counter += 1
        line_height = draw.textbbox((0, 0), line, font=font_orig)[3] - draw.textbbox((0, 0), line, font=font_orig)[1]
        y_text += line_height + extra_line_spacing

    # Draw separator line after the original segment (if translation exists)
    if translation_seg:
        y_text += separator_pre_margin
        draw.line([(separator_margin, y_text), (slide_size[0]-separator_margin, y_text)],
                  fill=separator_color, width=separator_thickness)
        y_text += separator_thickness + segment_spacing

    # --- Draw Translation Segment with Progressive Highlighting ---
    rtl_languages = {"Arabic", "Hebrew", "Urdu", "Persian"}
    is_rtl = any(lang in header_info for lang in rtl_languages) if header_info else False
    is_cjk = any(lang in header_info for lang in ["Chinese", "Japanese"])
    if translation_seg:
        if is_rtl:
            word_counter = 0
            for line in trans_lines:
                words_line = line.split()
                if not words_line:
                    continue
                space_bbox = draw.textbbox((0, 0), " ", font=font_trans)
                space_width = space_bbox[2] - space_bbox[0]
                total_width = sum((draw.textbbox((0, 0), w, font=font_trans)[2] - draw.textbbox((0, 0), w, font=font_trans)[0])
                                  for w in words_line) + space_width * (len(words_line)-1)
                x_line = (slide_size[0] - total_width) // 2 + total_width
                for w in words_line:
                    w_width = draw.textbbox((0, 0), w, font=font_trans)[2] - draw.textbbox((0, 0), w, font=font_trans)[0]
                    if word_counter < (translation_highlight_word_index or 0):
                        try:
                            highlight_font = ImageFont.truetype(default_font_path, int(font_trans.size * scale_factor))
                        except IOError:
                            highlight_font = font_trans
                        draw.text((x_line - w_width, y_text), w, font=highlight_font, fill=highlight_color)
                    else:
                        draw.text((x_line - w_width, y_text), w, font=font_trans, fill=translation_color)
                    x_line -= (w_width + space_width)
                    word_counter += 1
                line_height = draw.textbbox((0, 0), line, font=font_trans)[3] - draw.textbbox((0, 0), line, font=font_trans)[1]
                y_text += line_height + extra_line_spacing
        else:
            if is_cjk:
                char_counter = 0
                for line in trans_lines:
                    line_chars = list(line)
                    total_width = sum((draw.textbbox((0, 0), ch, font=font_trans)[2] - 
                                       draw.textbbox((0, 0), ch, font=font_trans)[0])
                                      for ch in line_chars)
                    x_line = (slide_size[0] - total_width) // 2
                    for ch in line_chars:
                        ch_width = draw.textbbox((0, 0), ch, font=font_trans)[2] - draw.textbbox((0, 0), ch, font=font_trans)[0]
                        if char_counter < (translation_highlight_word_index or 0):
                            try:
                                highlight_font = ImageFont.truetype(default_font_path, int(font_trans.size * scale_factor))
                            except IOError:
                                highlight_font = font_trans
                            draw.text((x_line, y_text), ch, font=highlight_font, fill=highlight_color)
                        else:
                            draw.text((x_line, y_text), ch, font=font_trans, fill=translation_color)
                        x_line += ch_width
                        char_counter += 1
                    line_height = draw.textbbox((0, 0), line, font=font_trans)[3] - draw.textbbox((0, 0), line, font=font_trans)[1]
                    y_text += line_height + extra_line_spacing
            else:
                word_counter = 0
                for line in trans_lines:
                    words_line = line.split()
                    space_bbox = draw.textbbox((0, 0), " ", font=font_trans)
                    space_width = space_bbox[2] - space_bbox[0]
                    total_width = sum((draw.textbbox((0, 0), w, font=font_trans)[2] - 
                                       draw.textbbox((0, 0), w, font=font_trans)[0])
                                      for w in words_line) + space_width * (len(words_line) - 1)
                    x_line = (slide_size[0] - total_width) // 2
                    for w in words_line:
                        if word_counter < (translation_highlight_word_index or 0):
                            try:
                                highlight_font = ImageFont.truetype(default_font_path, int(font_trans.size * scale_factor))
                            except IOError:
                                highlight_font = font_trans
                            draw.text((x_line, y_text), w, font=highlight_font, fill=highlight_color)
                        else:
                            draw.text((x_line, y_text), w, font=font_trans, fill=translation_color)
                        w_width = draw.textbbox((0, 0), w, font=font_trans)[2] - draw.textbbox((0, 0), w, font=font_trans)[0]
                        x_line += w_width + space_width
                        word_counter += 1
                    line_height = draw.textbbox((0, 0), line, font=font_trans)[3] - draw.textbbox((0, 0), line, font=font_trans)[1]
                    y_text += line_height + extra_line_spacing

    # If a transliteration segment exists, draw a separator before it
    if transliteration_seg:
        y_text += separator_pre_margin
        draw.line([(separator_margin, y_text), (slide_size[0]-separator_margin, y_text)],
                  fill=separator_color, width=separator_thickness)
        y_text += separator_thickness + segment_spacing

    # --- Draw Transliteration Segment (if present) ---
    if transliteration_seg:
        word_counter = 0
        for line in translit_lines:
            words_line = line.split()
            space_bbox = draw.textbbox((0, 0), " ", font=font_translit)
            space_width = space_bbox[2] - space_bbox[0]
            total_width = sum((draw.textbbox((0, 0), w, font=font_translit)[2] - 
                               draw.textbbox((0, 0), w, font=font_translit)[0])
                              for w in words_line) + space_width * (len(words_line)-1)
            x_line = (slide_size[0] - total_width) // 2
            for w in words_line:
                if word_counter < (transliteration_highlight_word_index or 0):
                    try:
                        highlight_font = ImageFont.truetype(default_font_path, int(font_translit.size * scale_factor))
                    except IOError:
                        highlight_font = font_translit
                    draw.text((x_line, y_text), w, font=highlight_font, fill=highlight_color)
                else:
                    draw.text((x_line, y_text), w, font=font_translit, fill=transliteration_color)
                w_bbox = draw.textbbox((0, 0), w, font=font_translit)
                w_width = w_bbox[2] - w_bbox[0]
                x_line += w_width + space_width
                word_counter += 1
            line_height = draw.textbbox((0, 0), line, font=font_translit)[3] - draw.textbbox((0, 0), line, font=font_translit)[1]
            y_text += line_height + extra_line_spacing

    return img
# -----------------------
# NEW: Generate a Word-Synced Sentence Video (with Audio Merging)
# -----------------------
def generate_word_synced_sentence_video(block, audio_seg, sentence_index, slide_size=(1280,720),
                                        initial_font_size=50, default_font_path="Arial.ttf",
                                        bg_color=(0,0,0), cover_img=None, header_info=""):
    """
    Generates a word-synced sentence video with progressive highlighting for:
      • Original text,
      • Translation,
      • Transliteration.

    On the last iteration, fraction is forced to 1.0 so that every word is highlighted
    by the final slide. Each short slide is concatenated into a single MP4, then merged
    with the provided audio segment.

    Arguments:
      block: a string containing multiple lines:
         1) [header info or language tags],
         2) original sentence,
         3) translation,
         4) optional transliteration
      audio_seg: a pydub AudioSegment for this sentence
      sentence_index: integer, used to label temporary output
      slide_size, initial_font_size, default_font_path, bg_color, cover_img, header_info:
         various layout parameters for the slide image
    """
    import os, subprocess

    # 1) Parse the block into original, translation, transliteration segments
    raw_lines = block.split("\n")
    content = "\n".join(raw_lines[1:]).strip()
    lines = [line.strip() for line in content.split("\n") if line.strip()]

    if len(lines) >= 3:
        original_seg = lines[0]
        translation_seg = lines[1]
        transliteration_seg = lines[2]
    elif len(lines) >= 2:
        original_seg = lines[0]
        translation_seg = " ".join(lines[1:])
        transliteration_seg = ""
    else:
        original_seg = translation_seg = content
        transliteration_seg = ""

    # Count words in original
    original_words = original_seg.split()
    num_original_words = len(original_words)

    # 2) Determine how to split the translation (words or chars)
    header_line = block.split("\n")[0]
    if "Chinese" in header_line or "Japanese" in header_line:
        translation_words = list(translation_seg)  # character-based
    else:
        translation_words = translation_seg.split()
        if not translation_words:
            translation_words = [translation_seg]
    num_translation_words = len(translation_words)

    # 3) If there's a transliteration segment, count words
    transliteration_words = transliteration_seg.split()
    num_translit_words = len(transliteration_words)

    # 4) Compute durations for each "unit" (word or char) in the translation
    audio_duration = audio_seg.duration_seconds
    sync_ratio = SYNC_RATIO  # If you have a global variable for time ratio
    total_letters = sum(len(w) for w in translation_words)  # used for weighting

    word_durations = []
    for w in translation_words:
        if total_letters > 0:
            dur = (len(w) / total_letters) * audio_duration * sync_ratio
        else:
            # fallback if somehow the translation is empty
            dur = (audio_duration / max(1, len(translation_words))) * sync_ratio
        word_durations.append(dur)

    video_duration = sum(word_durations)
    pad_duration = audio_duration - video_duration
    if pad_duration < 0:
        pad_duration = 0

    word_video_files = []
    accumulated_time = 0

    # 5) For each translation "word" (or char), generate a slide
    for idx, duration in enumerate(word_durations):
        accumulated_time += duration

        # fraction of audio elapsed
        if idx == len(word_durations) - 1:
            # Force fraction = 1.0 on the last iteration
            fraction = 1.0
        else:
            fraction = accumulated_time / audio_duration

        # Compute highlight indices for each segment, cumulatively
        original_highlight_index = int(fraction * num_original_words) if num_original_words else 0
        translation_highlight_index = int(fraction * num_translation_words) if num_translation_words else 0
        transliteration_highlight_index = int(fraction * num_translit_words) if num_translit_words else 0

        # Now generate the slide
        img = generate_sentence_slide_image(
            block,
            original_highlight_word_index=original_highlight_index,
            translation_highlight_word_index=translation_highlight_index,
            transliteration_highlight_word_index=transliteration_highlight_index,
            slide_size=slide_size,
            initial_font_size=initial_font_size,
            default_font_path=default_font_path,
            bg_color=bg_color,
            cover_img=cover_img,
            header_info=header_info
        )

        # Save this slide as a PNG, then create a short MP4
        img_path = os.path.join(TMP_DIR, f"word_slide_{sentence_index}_{idx}.png")
        img.save(img_path)

        video_path = os.path.join(TMP_DIR, f"word_slide_{sentence_index}_{idx}.mp4")
        cmd = [
            "ffmpeg",
            "-loglevel", "quiet",
            "-y",
            "-loop", "1",
            "-i", img_path,
            # We need a short silent audio input for ffmpeg to create a video
            "-i", os.path.join(TMP_DIR, "silence.wav"),
            "-c:v", "libx264",
            "-t", f"{duration:.2f}",
            "-pix_fmt", "yuv420p",
            "-vf", "format=yuv420p",
            "-an",  # no audio here
            video_path
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error on word slide {sentence_index}_{idx}: {e}")

        word_video_files.append(video_path)
        os.remove(img_path)

    # 6) Concatenate all short MP4 segments
    concat_list_path = os.path.join(TMP_DIR, f"concat_word_{sentence_index}.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for video_file in word_video_files:
            f.write(f"file '{video_file}'\n")

    sentence_video_path = os.path.join(TMP_DIR, f"sentence_slide_{sentence_index}.mp4")
    cmd_concat = [
        "ffmpeg",
        "-loglevel", "quiet",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        sentence_video_path
    ]
    try:
        result = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print("FFmpeg concat error:", result.stderr.decode())
            raise subprocess.CalledProcessError(result.returncode, cmd_concat)
    except subprocess.CalledProcessError as e:
        print(f"Error concatenating word slides for sentence {sentence_index}: {e}")

    os.remove(concat_list_path)
    for vf in word_video_files:
        if os.path.exists(vf):
            os.remove(vf)

    # 7) Merge with the real sentence audio
    audio_temp_path = os.path.join(TMP_DIR, f"sentence_audio_{sentence_index}.wav")
    audio_seg.export(audio_temp_path, format="wav")
    merged_video_path = os.path.join(TMP_DIR, f"sentence_slide_{sentence_index}_merged.mp4")

    cmd_merge = [
        "ffmpeg",
        "-loglevel", "quiet",
        "-y",
        "-i", sentence_video_path,
        "-i", audio_temp_path,
        "-c:v", "copy",
        "-c:a", "aac",
        merged_video_path
    ]
    try:
        subprocess.run(cmd_merge, check=True)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error merging audio for sentence {sentence_index}: {e}")

    os.remove(audio_temp_path)
    os.remove(sentence_video_path)

    # 8) If there’s leftover time, pad the final video so its length matches the audio
    final_video_path = os.path.join(TMP_DIR, f"sentence_slide_{sentence_index}_final.mp4")
    if pad_duration > 0:
        cmd_tpad = [
            "ffmpeg",
            "-loglevel", "quiet",
            "-y",
            "-i", merged_video_path,
            "-vf", f"tpad=stop_mode=clone:stop_duration={pad_duration:.2f}",
            "-af", f"apad=pad_dur={pad_duration:.2f}",
            final_video_path
        ]
        try:
            subprocess.run(cmd_tpad, check=True)
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error adding pad for sentence {sentence_index}: {e}")
        os.remove(merged_video_path)
    else:
        # No leftover time, just rename merged to final
        os.rename(merged_video_path, final_video_path)

    return final_video_path

# -----------------------
# Modified Function: Video Slide Generation with Word-Level Syncing
# -----------------------
def generate_video_slides_ffmpeg(text_blocks, audio_segments, output_dir, batch_start, batch_end, base_no_ext,
                                 cover_img, book_author, book_title, cumulative_word_counts, total_word_count,
                                 macos_reading_speed, cleanup=True,
                                 slide_size=(1280,720), initial_font_size=60, bg_color=(0,0,0)):
    print(f"Generating video slide set for sentences {batch_start} to {batch_end}...")
    sentence_video_files = []
    silence_audio_path = os.path.join(TMP_DIR, "silence.wav")
    if not os.path.exists(silence_audio_path):
        silent = AudioSegment.silent(duration=100)
        silent.export(silence_audio_path, format="wav")
        
    for idx, (block, audio_seg) in enumerate(zip(text_blocks, audio_segments)):
        sentence_number = batch_start + idx
        words_processed = cumulative_word_counts[sentence_number - 1]
        remaining_words = total_word_count - words_processed
        if macos_reading_speed > 0:
            est_seconds = int(remaining_words * 60 / macos_reading_speed)
        else:
            est_seconds = 0
        hours = est_seconds // 3600
        minutes = (est_seconds % 3600) // 60
        seconds = est_seconds % 60
        remaining_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        header_tokens = block.split("\n")[0].split(" - ")
        target_lang = header_tokens[0].strip() if header_tokens else ""
        total_fully = len(refined_list)
        progress_percentage = (sentence_number / total_fully) * 100
        header_info = (f"Book: {book_title} | Author: {book_author}\n"
               f"Source Language: {input_language} | Target: {target_lang} | Speed: {TEMPO}\n"
               f"Sentence: {sentence_number}/{total_fully} | Progress: {progress_percentage:.2f}% | Remaining: {remaining_time_str}")
        
        try:
            sentence_video = generate_word_synced_sentence_video(block, audio_seg, sentence_number,
                                                                 slide_size=slide_size, initial_font_size=initial_font_size,
                                                                 default_font_path=get_default_font_path(), bg_color=bg_color,
                                                                 cover_img=cover_img, header_info=header_info)
            sentence_video_files.append(sentence_video)
        except Exception as e:
            print(f"Error generating sentence video for sentence {sentence_number}: {e}")
    concat_list_path = os.path.join(output_dir, f"concat_{batch_start}_{batch_end}.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for video_file in sentence_video_files:
            f.write(f"file '{video_file}'\n")
    final_video_path = os.path.join(output_dir, f"{batch_start}-{batch_end}_{base_no_ext}.mp4")
    cmd_concat = [
        "ffmpeg",
        "-loglevel", "quiet",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        final_video_path
    ]
    try:
        result = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print("FFmpeg final concat error:", result.stderr.decode())
            raise subprocess.CalledProcessError(result.returncode, cmd_concat)
    except subprocess.CalledProcessError as e:
        print(f"Error concatenating sentence slides: {e}")
    os.remove(concat_list_path)
    print(f"Final stitched video slide output saved to: {final_video_path}")
    
    for video_file in sentence_video_files:
        if os.path.exists(video_file):
            os.remove(video_file)
    if os.path.exists(silence_audio_path):
        os.remove(silence_audio_path)
    return final_video_path

# -----------------------
# Main EPUB Processing Function
# -----------------------
def process_epub(input_file, base_output_file, input_language, target_languages,
                 sentences_per_file, start_sentence, end_sentence,
                 generate_audio, audio_mode, written_mode, output_html, output_pdf,
                 refined_list, generate_video, include_transliteration=False,
                 book_metadata={}):
    print(f"\nExtracting text from '{input_file}'...")
    total_fully = len(refined_list)
    print(f"Total fully split sentences extracted: {total_fully}")
    start_idx = max(start_sentence - 1, 0)
    end_idx = end_sentence if (end_sentence is not None and end_sentence <= total_fully) else total_fully
    selected_sentences = refined_list[start_idx:end_idx]
    total_refined = len(selected_sentences)
    print(f"Processing {total_refined} sentences starting from refined sentence #{start_sentence}")
    
    target_lang_str = "_".join(target_languages)
    base = os.path.splitext(os.path.basename(input_file))[0]
    base_dir = os.path.join(EBOOK_DIR, f"{target_lang_str}_{base}")
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    base_output_file = os.path.join(base_dir, f"{target_lang_str}_{base}.html")
    base_no_ext = f"{target_lang_str}_{base}"
    
    book_title = book_metadata.get("book_title", "Unknown Title")
    book_author = book_metadata.get("book_author", "Unknown Author")
    
    cover_img = None
    cover_file = book_metadata.get("book_cover_file")
    if cover_file and os.path.exists(cover_file):
        try:
            cover_img = Image.open(cover_file)
        except Exception as e:
            if DEBUG:
                print("Error loading cover image from file:", e)
            cover_img = None
    else:
        cover_img = fetch_book_cover(f"{book_title} {book_author}")
    
    global_cumulative_word_counts = []
    running = 0
    for s in refined_list:
        running += len(s.split())
        global_cumulative_word_counts.append(running)
    total_book_words = running
    
    written_blocks = []
    video_blocks = []
    all_audio_segments = [] if generate_audio else None
    batch_video_files = []
    current_audio = [] if generate_audio else None
    current_batch_start = start_sentence
    for i, sentence in enumerate(tqdm(selected_sentences, desc="Processing sentences", unit="sentence"), start=start_sentence):
        current_target = target_languages[(i - start_sentence) % len(target_languages)]
        if include_transliteration and current_target in NON_LATIN_LANGUAGES:
            translation_result = translate_sentence_simple(sentence, input_language, current_target, include_transliteration=False)
            translation_result = remove_quotes(translation_result)
            transliteration_result = transliterate_sentence(translation_result, current_target)
            transliteration_result = remove_quotes(transliteration_result)
            fluent = translation_result
            if written_mode == "1":
                written_block = f"{fluent}\n"
            elif written_mode == "2":
                written_block = f"{i} - {(i/total_fully*100):.2f}%\n{fluent}\n"
            elif written_mode == "3":
                written_block = f"{i} - {(i/total_fully*100):.2f}%\n{sentence}\n\n{fluent}\n"
            else:
                written_block = f"{sentence}\n\n{fluent}\n"
            written_block = written_block.rstrip() + f"\n{transliteration_result}\n"
            video_block = f"{current_target} - {i} - {(i/total_fully*100):.2f}%\n{sentence}\n\n{fluent}\n{transliteration_result}\n"
        else:
            fluent = translate_sentence_simple(sentence, input_language, current_target)
            fluent = remove_quotes(fluent)
            if written_mode == "1":
                written_block = f"{fluent}\n"
            elif written_mode == "2":
                written_block = f"{i} - {(i/total_fully*100):.2f}%\n{fluent}\n"
            elif written_mode == "3":
                written_block = f"{i} - {(i/total_fully*100):.2f}%\n{sentence}\n\n{fluent}\n"
            else:
                written_block = f"{sentence}\n\n{fluent}\n"
            video_block = f"{current_target} - {i} - {(i/total_fully*100):.2f}%\n{sentence}\n\n{fluent}\n"
        written_blocks.append(written_block)
        if generate_video:
            video_blocks.append(video_block)
        if generate_audio:
            audio_seg = generate_audio_for_sentence(i, sentence, fluent, input_language, current_target, audio_mode, total_fully)
            current_audio.append(audio_seg)
            all_audio_segments.append(audio_seg)
        if (i - start_sentence + 1) % sentences_per_file == 0:
            batch_start = current_batch_start
            batch_end = i
            if output_html:
                html_filename = os.path.join(base_dir, f"{batch_start}-{batch_end}_{base_no_ext}.html")
                write_html_file(html_filename, written_blocks)
            if output_pdf:
                pdf_filename = os.path.join(base_dir, f"{batch_start}-{batch_end}_{base_no_ext}.pdf")
                write_pdf_file(pdf_filename, written_blocks, current_target)
            if generate_audio and current_audio:
                combined = AudioSegment.empty()
                for seg in current_audio:
                    combined += seg
                audio_filename = os.path.join(base_dir, f"{batch_start}-{batch_end}_{base_no_ext}.mp3")
                combined.export(audio_filename, format="mp3", bitrate="320k")
            if generate_video and current_audio:
                video_path = generate_video_slides_ffmpeg(video_blocks, current_audio, base_dir, batch_start, batch_end, base_no_ext,
                                                          cover_img, book_author, book_title,
                                                          global_cumulative_word_counts, total_book_words,
                                                          MACOS_READING_SPEED)
                batch_video_files.append(video_path)
            written_blocks = []
            video_blocks = []
            if generate_audio:
                current_audio = []
            current_batch_start = i + 1
    if written_blocks:
        batch_start = current_batch_start
        batch_end = start_sentence + len(written_blocks) - 1
        if output_html:
            html_filename = os.path.join(base_dir, f"{batch_start}-{batch_end}_{base_no_ext}.html")
            write_html_file(html_filename, written_blocks)
        if output_pdf:
            pdf_filename = os.path.join(base_dir, f"{batch_start}-{batch_end}_{base_no_ext}.pdf")
            write_pdf_file(pdf_filename, written_blocks, target_languages[0])
        if generate_audio and current_audio:
            combined = AudioSegment.empty()
            for seg in current_audio:
                combined += seg
            audio_filename = os.path.join(base_dir, f"{batch_start}-{batch_end}_{base_no_ext}.mp3")
            combined.export(audio_filename, format="mp3", bitrate="320k")
        if generate_video and current_audio:
            video_path = generate_video_slides_ffmpeg(video_blocks, current_audio, base_dir, batch_start, batch_end, base_no_ext,
                                                      cover_img, book_author, book_title,
                                                      global_cumulative_word_counts, total_book_words,
                                                      MACOS_READING_SPEED)
            batch_video_files.append(video_path)
    print("\nEPUB processing complete!")
    print(f"Total sentences processed: {total_refined}")
    return written_blocks, all_audio_segments, batch_video_files

# -----------------------
# Interactive Menu with Grouped Options and Dynamic Summary
# -----------------------
def interactive_menu():
    global OLLAMA_MODEL, DEBUG, SELECTED_VOICE, MAX_WORDS, EXTEND_SPLIT_WITH_COMMA_SEMICOLON, MACOS_READING_SPEED, SYNC_RATIO, WORD_HIGHLIGHTING, TEMPO
    config = {}
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            print(f"\nLoaded configuration from {config_file}")
        except Exception as e:
            print(f"\nError loading config file: {e}. Proceeding with defaults.")
            config = {}
    else:
        config = {}

    config.setdefault("input_file", "")
    config.setdefault("base_output_file", "")
    config.setdefault("input_language", "English")
    config.setdefault("target_languages", ["Arabic"])
    config.setdefault("ollama_model", DEFAULT_MODEL)
    config.setdefault("generate_audio", True)
    config.setdefault("generate_video", True)
    config.setdefault("sentences_per_output_file", 10)
    config.setdefault("start_sentence", 1)
    config.setdefault("end_sentence", None)
    config.setdefault("max_words", 18)
    config.setdefault("percentile", 96)
    config.setdefault("split_on_comma_semicolon", False)
    config.setdefault("audio_mode", "1")
    config.setdefault("written_mode", "4")
    config.setdefault("include_transliteration", False)
    config.setdefault("debug", False)
    config.setdefault("output_html", True)
    config.setdefault("output_pdf", False)
    config.setdefault("stitch_full", False)
    config.setdefault("selected_voice", "gTTS")
    config.setdefault("book_title", "Unknown Title")
    config.setdefault("book_author", "Unknown Author")
    config.setdefault("book_year", "Unknown Year")
    config.setdefault("book_summary", "No summary provided.")
    config.setdefault("book_cover_file", None)
    config.setdefault("macos_reading_speed", 100)
    config.setdefault("tempo", 1.0)  # New tempo default
    config.setdefault("sync_ratio", 0.9)
    config.setdefault("word_highlighting", True)

    if "start_sentence" in config and not str(config["start_sentence"]).isdigit():
        config["start_sentence_lookup"] = config["start_sentence"]

    config = update_book_cover_file_in_config(config)

    if config.get("input_file"):
        text = extract_text_from_epub(config["input_file"])
        refined = split_text_into_sentences(text)
    else:
        refined = []
    config = update_sentence_config(config, refined)
    EXTEND_SPLIT_WITH_COMMA_SEMICOLON = config.get("split_on_comma_semicolon", False)

    while True:
        if config.get("input_file"):
            text = extract_text_from_epub(config["input_file"])
            refined = split_text_into_sentences(text)
            config["refined_list"] = refined
        else:
            refined = []
        config = update_sentence_config(config, refined)

        print("\n--- File / Language Settings ---")
        print(f"1. Input EPUB file: {config.get('input_file', '')}")
        print(f"2. Base output file: {config.get('base_output_file', '')}")
        print(f"3. Input language: {config.get('input_language', 'English')}")
        print(f"4. Target languages: {', '.join(config.get('target_languages', ['Arabic']))}")
        
        print("\n--- LLM, Audio, Video Settings ---")
        print(f"5. Ollama model: {config.get('ollama_model', DEFAULT_MODEL)}")
        print(f"6. Generate audio output: {config.get('generate_audio', True)}")
        print(f"7. Generate video slide output: {config.get('generate_video', False)}")
        print(f"8. Selected voice for audio generation: {config.get('selected_voice', 'gTTS')}")
        print(f"9. macOS TTS reading speed (words per minute): {config.get('macos_reading_speed', 100)}")
        print(f"10. Audio tempo (default: {config.get('tempo', 1.0)})")
        print(f"11. Sync ratio for word slides: {config.get('sync_ratio', 0.9)}")
        
        print("\n--- Sentence Parsing Settings ---")
        print(f"12. Sentences per output file: {config.get('sentences_per_output_file', 10)}")
        print(f"13. Starting sentence (number or lookup word): {config.get('start_sentence', 1)}")
        print(f"14. Ending sentence (absolute or offset): {config.get('end_sentence', f'Last sentence [{len(refined)}]')}")
        print(f"15. Max words per sentence chunk: {config.get('max_words', 18)}")
        print(f"16. Percentile for computing suggested max words: {config.get('percentile', 96)}")
        
        print("\n--- Format Options ---")
        print(f"17. Audio output mode: {config.get('audio_mode', '1')} ({AUDIO_MODE_DESC.get(config.get('audio_mode', '1'), '')})")
        print(f"18. Written output mode: {config.get('written_mode', '4')} ({WRITTEN_MODE_DESC.get(config.get('written_mode', '4'), '')})")
        print(f"19. Extend split logic with comma and semicolon: {'Yes' if config.get('split_on_comma_semicolon', False) else 'No'}")
        print(f"20. Include transliteration for non-Latin alphabets: {config.get('include_transliteration', False)}")
        print(f"21. Word highlighting for video slides: {'Yes' if config.get('word_highlighting', True) else 'No'}")
        print(f"22. Debug mode: {config.get('debug', False)}")
        print(f"23. HTML output: {config.get('output_html', True)}")
        print(f"24. PDF output: {config.get('output_pdf', False)}")
        print(f"25. Generate stitched full output file: {config.get('stitch_full', False)}")
        
        print("\n--- Book Metadata ---")
        print(f"26. Book Title: {config.get('book_title')}")
        print(f"27. Author: {config.get('book_author')}")
        print(f"28. Year: {config.get('book_year')}")
        print(f"29. Summary: {config.get('book_summary')}")
        print(f"30. Book Cover File: {config.get('book_cover_file', 'None')}")
        
        inp_choice = input("\nEnter a parameter number to change (or press Enter to confirm): ").strip()
        if inp_choice == "":
            break
        elif inp_choice.isdigit():
            num = int(inp_choice)
            if num == 1:
                epub_files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]
                for idx, file in enumerate(epub_files, start=1):
                    print(f"{idx}. {file}")
                default_input = config.get("input_file", epub_files[0] if epub_files else "")
                inp_val = input(f"Select an input file by number (default: {default_input}): ").strip()
                if inp_val.isdigit():
                    config["input_file"] = epub_files[int(inp_val)-1]
                else:
                    config["input_file"] = default_input
            elif num == 2:
                if config.get("input_file"):
                    base = os.path.splitext(os.path.basename(config["input_file"]))[0]
                    default_file = os.path.join(EBOOK_DIR, base, f"{', '.join(config.get('target_languages', ['Arabic']))}_{base}.html")
                else:
                    default_file = os.path.join(EBOOK_DIR, "output.html")
                inp_val = input(f"Enter base output file name (default: {default_file}): ").strip()
                config["base_output_file"] = inp_val if inp_val else default_file
            elif num == 3:
                print("\nSelect input language:")
                print_languages_in_four_columns()
                default_in = config.get("input_language", "English")
                inp_val = input(f"Select input language by number (default: {default_in}): ").strip()
                if inp_val.isdigit():
                    config["input_language"] = TOP_LANGUAGES[int(inp_val)-1]
                else:
                    config["input_language"] = default_in
            elif num == 4:
                print("\nSelect target languages (separate choices by comma, e.g. 1,4,7):")
                print_languages_in_four_columns()
                default_t = config.get("target_languages", ["Arabic"])
                inp_val = input(f"Select target languages by number (default: {', '.join(default_t)}): ").strip()
                if inp_val:
                    choices = [int(x) for x in inp_val.split(",") if x.strip().isdigit()]
                    selected_langs = [TOP_LANGUAGES[x-1] for x in choices if 0 < x <= len(TOP_LANGUAGES)]
                    config["target_languages"] = selected_langs if selected_langs else default_t
                else:
                    config["target_languages"] = default_t
            elif num == 5:
                try:
                    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
                    models = result.stdout.strip().split("\n")[1:]
                    for idx, model in enumerate(models, start=1):
                        print(f"{idx}. {model}")
                    default_model = config.get("ollama_model", models[0].split()[0])
                    inp_val = input(f"Select a model by number (default: {default_model}): ").strip()
                    if inp_val.isdigit():
                        config["ollama_model"] = models[int(inp_val)-1].split()[0]
                    else:
                        config["ollama_model"] = default_model
                except Exception as e:
                    print(f"Error listing models: {e}")
            elif num == 6:
                default_audio = config.get("generate_audio", True)
                inp_val = input(f"Generate audio output files? (yes/no, default {'yes' if default_audio else 'no'}): ").strip().lower()
                config["generate_audio"] = True if inp_val in ["", "yes", "y"] else False
            elif num == 7:
                default_video = config.get("generate_video", False)
                inp_val = input(f"Generate video slide output? (yes/no, default {'yes' if default_video else 'no'}): ").strip().lower()
                config["generate_video"] = True if inp_val in ["yes", "y"] else False
            elif num == 8:
                default_voice = config.get("selected_voice", "gTTS")
                print("\nSelect voice for audio generation:")
                print("1. Use gTTS (online text-to-speech)")
                print("2. Use macOS TTS voice (only Enhanced/Premium voices shown)")
                voice_choice = input("Enter 1 for gTTS or 2 for macOS voice (default: 1): ").strip()
                if voice_choice == "2":
                    voices = get_macOS_voices()
                    if voices:
                        print("Available macOS voices (Enhanced/Premium):")
                        for idx, v in enumerate(voices, start=1):
                            print(f"{idx}. {v}")
                        inp = input(f"Select a macOS voice by number (default: {voices[0]}): ").strip()
                        if inp.isdigit() and 1 <= int(inp) <= len(voices):
                            voice_selected = voices[int(inp)-1]
                        else:
                            voice_selected = voices[0]
                    else:
                        print("No macOS voices found, defaulting to gTTS")
                        voice_selected = "gTTS"
                else:
                    voice_selected = "gTTS"
                config["selected_voice"] = voice_selected
            elif num == 9:
                default_reading_speed = config.get("macos_reading_speed", 100)
                inp_val = input(f"Enter macOS TTS reading speed (words per minute) (default {default_reading_speed}): ").strip()
                config["macos_reading_speed"] = int(inp_val) if inp_val.isdigit() else default_reading_speed
            elif num == 10:
                default_tempo = config.get("tempo", 1.0)
                inp_val = input(f"Enter audio tempo (e.g. 1 for normal, 1.5 for faster, 0.75 for slower) (default {default_tempo}): ").strip()
                try:
                    config["tempo"] = float(inp_val) if inp_val else default_tempo
                except:
                    config["tempo"] = default_tempo
            elif num == 11:
                default_sync = config.get("sync_ratio", 0.9)
                inp_val = input(f"Enter sync ratio for word slides (default {default_sync}): ").strip()
                try:
                    new_sync = float(inp_val)
                    config["sync_ratio"] = new_sync
                except:
                    config["sync_ratio"] = default_sync
            elif num == 12:
                default_sent = config.get("sentences_per_output_file", 10)
                inp_val = input(f"Enter number of sentences per output file (default {default_sent}): ").strip()
                config["sentences_per_output_file"] = int(inp_val) if inp_val.isdigit() else default_sent
            elif num == 13:
                default_start = config.get("start_sentence", 1)
                inp_val = input(f"Enter starting sentence (number or lookup word) (default: {default_start}): ").strip()
                if inp_val:
                    if inp_val.isdigit():
                        config["start_sentence"] = int(inp_val)
                        config["start_sentence_lookup"] = ""
                    else:
                        config["start_sentence_lookup"] = inp_val
                        config["start_sentence"] = inp_val
                else:
                    config["start_sentence"] = default_start
            elif num == 14:
                total_sent = len(refined)
                default_end = config.get("end_sentence")
                inp_val = input(f"Enter ending sentence (absolute or offset, e.g. +100) (default: last sentence [{total_sent}]): ").strip()
                if inp_val == "":
                    config["end_sentence"] = total_sent
                elif inp_val[0] in ['+', '-']:
                    try:
                        offset = int(inp_val)
                        start_val = int(config.get("start_sentence", 1))
                        config["end_sentence"] = start_val + offset
                        print(f"Ending sentence updated to {config['end_sentence']}")
                    except Exception:
                        config["end_sentence"] = default_end
                elif inp_val.isdigit():
                    config["end_sentence"] = int(inp_val)
                else:
                    config["end_sentence"] = default_end
            elif num == 15:
                default_max = config.get("max_words", 18)
                inp_val = input(f"Enter maximum words per sentence chunk (default {default_max}): ").strip()
                if inp_val.isdigit():
                    new_max = int(inp_val)
                    config["max_words"] = new_max
                    config["max_words_manual"] = True
                    text = extract_text_from_epub(config["input_file"])
                    refined_tmp = split_text_into_sentences(text)
                    lengths = [len(s.split()) for s in refined_tmp]
                    new_perc = None
                    for i, length in enumerate(lengths):
                        if length >= new_max:
                            new_perc = int(((i+1) / len(lengths)) * 100)
                            break
                    config["percentile"] = new_perc if new_perc is not None else 100
                    print(f"Recomputed percentile based on new max words: {config['percentile']}%")
                else:
                    config["max_words"] = default_max
            elif num == 16:
                default_perc = config.get("percentile", 96)
                inp_val = input(f"Enter percentile for computing suggested max words (0-100) (default {default_perc}): ").strip()
                if inp_val.isdigit():
                    p_val = int(inp_val)
                    if 0 < p_val <= 100:
                        config["percentile"] = p_val
                        text = extract_text_from_epub(config["input_file"])
                        refined_tmp = split_text_into_sentences(text)
                        if refined_tmp:
                            lengths = [len(s.split()) for s in refined_tmp]
                            lengths.sort()
                            idx_p = int((p_val/100.0) * len(lengths))
                            config["max_words"] = lengths[idx_p] if idx_p < len(lengths) else lengths[-1]
                        print(f"Updated percentile to {p_val}%, and max words set to {config['max_words']}")
                    else:
                        print("Invalid percentile, must be between 1 and 100. Keeping previous value.")
                else:
                    config["percentile"] = default_perc
            elif num == 17:
                default_am = config.get("audio_mode", "1")
                print("\nChoose audio output mode:")
                print("1: Only translated sentence")
                print("2: Sentence numbering + translated sentence")
                print("3: Full original format (numbering, original sentence, translated sentence)")
                print("4: Original sentence + translated sentence")
                inp_val = input(f"Select audio output mode (default {default_am}): ").strip()
                config["audio_mode"] = inp_val if inp_val in ["1", "2", "3", "4"] else default_am
            elif num == 18:
                default_wm = config.get("written_mode", "4")
                print("\nChoose written output mode:")
                print("1: Only fluent translation")
                print("2: Sentence numbering + fluent translation")
                print("3: Full original format (numbering, original sentence, fluent translation)")
                print("4: Original sentence + fluent translation")
                inp_val = input(f"Select written output mode (default {default_wm}): ").strip()
                config["written_mode"] = inp_val if inp_val in ["1", "2", "3", "4"] else default_wm
            elif num == 19:
                default_extend = config.get("split_on_comma_semicolon", False)
                inp_val = input(f"Extend split logic with comma and semicolon? (yes/no, default {'yes' if default_extend else 'no'}): ").strip().lower()
                config["split_on_comma_semicolon"] = True if inp_val in ["yes", "y"] else False
            elif num == 20:
                default_translit = config.get("include_transliteration", False)
                inp_val = input(f"Include transliteration for non-Latin alphabets? (yes/no, default {'yes' if default_translit else 'no'}): ").strip().lower()
                config["include_transliteration"] = True if inp_val in ["yes", "y"] else False
            elif num == 21:
                default_highlight = config.get("word_highlighting", True)
                inp_val = input(f"Enable word highlighting for video slides? (yes/no, default {'yes' if default_highlight else 'no'}): ").strip().lower()
                config["word_highlighting"] = True if inp_val in ["", "yes", "y"] else False
            elif num == 22:
                default_debug = config.get("debug", False)
                inp_val = input(f"Enable debug mode? (yes/no, default {'yes' if default_debug else 'no'}): ").strip().lower()
                config["debug"] = True if inp_val == "yes" else False
            elif num == 23:
                default_html = config.get("output_html", True)
                inp_val = input(f"HTML output? (yes/no, default {'yes' if default_html else 'no'}): ").strip().lower()
                config["output_html"] = True if inp_val in ["", "yes", "y"] else False
            elif num == 24:
                default_pdf = config.get("output_pdf", False)
                inp_val = input(f"PDF output? (yes/no, default {'yes' if default_pdf else 'no'}): ").strip().lower()
                config["output_pdf"] = True if inp_val in ["", "yes", "y"] else False
            elif num == 25:
                default_stitch = config.get("stitch_full", False)
                inp_val = input(f"Generate stitched full output file? (yes/no, default {'yes' if default_stitch else 'no'}): ").strip().lower()
                config["stitch_full"] = True if inp_val in ["yes", "y"] else False
            elif num == 26:
                inp_val = input("Enter Book Title: ").strip()
                config["book_title"] = inp_val if inp_val else config.get("book_title")
            elif num == 27:
                inp_val = input("Enter Book Author: ").strip()
                config["book_author"] = inp_val if inp_val else config.get("book_author")
            elif num == 28:
                inp_val = input("Enter Book Year: ").strip()
                config["book_year"] = inp_val if inp_val else config.get("book_year")
            elif num == 29:
                inp_val = input("Enter a short Summary of the Book: ").strip()
                config["book_summary"] = inp_val if inp_val else config.get("book_summary")
            elif num == 30:
                inp_val = input("Enter full path for Book Cover file (or leave blank to use default): ").strip()
                if inp_val:
                    if os.path.exists(inp_val):
                        config["book_cover_file"] = inp_val
                    else:
                        print("File does not exist. Keeping previous value.")
                else:
                    config = update_book_cover_file_in_config(config)
            else:
                print("Invalid parameter number. Please try again.")
        else:
            print("Invalid input. Please enter a number or press Enter.")
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            print(f"Configuration saved to {config_file}")
        except Exception as e:
            print(f"Error saving configuration: {e}")
    OLLAMA_MODEL = config.get("ollama_model", DEFAULT_MODEL)
    MAX_WORDS = config.get("max_words", 18)
    MACOS_READING_SPEED = config.get("macos_reading_speed", 100)
    SYNC_RATIO = config.get("sync_ratio", 0.9)
    WORD_HIGHLIGHTING = config.get("word_highlighting", True)
    TEMPO = config.get("tempo", 1.0)
    cmd_parts = [
        sys.executable, os.path.basename(__file__),
        f"\"{config['input_file']}\"",
        f"\"{config['input_language']}\"",
        f"\"{','.join(config['target_languages'])}\"",
        str(config["sentences_per_output_file"]),
        f"\"{config['base_output_file']}\"",
        str(config["start_sentence"])
    ]
    if config.get("end_sentence") is not None:
        cmd_parts.append(str(config["end_sentence"]))
    if config["debug"]:
        cmd_parts.append("--debug")
    full_command = " ".join(cmd_parts)
    print("\nTo run non-interactively with these settings, use the following command:")
    print(full_command)
    book_metadata = {
        "book_title": config.get("book_title"),
        "book_author": config.get("book_author"),
        "book_year": config.get("book_year"),
        "book_summary": config.get("book_summary"),
        "book_cover_file": config.get("book_cover_file")
    }
    return (
        config["input_file"], config["base_output_file"], config["input_language"],
        config["target_languages"], config["sentences_per_output_file"], config["start_sentence"],
        config.get("end_sentence"), config["stitch_full"], config["generate_audio"],
        config["audio_mode"], config["written_mode"], config.get("selected_voice", "gTTS"),
        config.get("output_html", True), config.get("output_pdf", False), config.get("generate_video", False),
        config.get("include_transliteration", False), config.get("tempo", 1.0), book_metadata
    )

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "-i":
        (input_file, base_output_file, input_language, target_languages,
         sentences_per_output_file, start_sentence, end_sentence, stitch_full,
         generate_audio, audio_mode, written_mode, selected_voice,
         output_html, output_pdf, generate_video, include_transliteration, tempo, book_metadata) = interactive_menu()
        SELECTED_VOICE = selected_voice
        TEMPO = tempo
    elif len(sys.argv) >= 2:
        input_file = sys.argv[1]
        input_language = sys.argv[2] if len(sys.argv) > 2 else "English"
        if len(sys.argv) > 3:
            target_language_input = sys.argv[3]
            if ',' in target_language_input:
                target_languages = [x.strip() for x in target_language_input.split(',')]
            else:
                target_languages = [target_language_input.strip()]
        else:
            target_languages = ["Arabic"]
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        target_lang_str = "_".join(target_languages)
        output_folder = os.path.join(EBOOK_DIR, f"{target_lang_str}_{base_name}")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        sentences_per_output_file = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 10
        base_output_file = os.path.join(output_folder, f"{target_lang_str}_{base_name}.html")
        start_sentence = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6].isdigit() else 1
        if len(sys.argv) > 7:
            end_in = sys.argv[7]
            if end_in.startswith('+') or end_in.startswith('-'):
                end_sentence = start_sentence + int(end_in)
            elif end_in.isdigit():
                end_sentence = int(end_in)
            else:
                end_sentence = None
        else:
            end_sentence = None
        stitch_full = False
        generate_audio = True
        audio_mode = "1"
        written_mode = "4"
        SELECTED_VOICE = "gTTS"
        output_html = True
        output_pdf = False
        generate_video = False
        include_transliteration = False
        # TEMPO remains default (1.0) in non-interactive mode
        book_metadata = {"book_title": "Unknown Title", "book_author": "Unknown Author", "book_year": "Unknown Year", "book_summary": "No summary provided.", "book_cover_file": None}
        if "--debug" in sys.argv:
            DEBUG = True
    else:
        print("Usage:")
        print("  python script.py -i")
        print("  or")
        print("  python script.py <input_epub_file> [<input_language>] [<target_languages_comma_separated>] [<sentences_per_output_file>]")
        print("         [<base_output_file>] [<start_sentence>] [<end_sentence>] [--debug]")
        sys.exit(1)
    try:
        print("\nStarting EPUB processing...")
        print(f"Input file: {input_file}")
        print(f"Base output file: {base_output_file}")
        print(f"Input language: {input_language}")
        print(f"Target languages: {', '.join(target_languages)}")
        print(f"Sentences per output file: {sentences_per_output_file}")
        print(f"Starting from sentence: {start_sentence}")
        if end_sentence:
            print(f"Ending at sentence: {end_sentence}")
        else:
            print("Processing until end of file")
        text = extract_text_from_epub(input_file)
        refined_list = split_text_into_sentences(text)
        written_blocks, all_audio_segments, batch_video_files = process_epub(
            input_file, base_output_file, input_language, target_languages,
            sentences_per_output_file, start_sentence, end_sentence,
            generate_audio, audio_mode, written_mode, output_html, output_pdf,
            refined_list=refined_list, generate_video=generate_video, include_transliteration=include_transliteration,
            book_metadata=book_metadata
        )
        if stitch_full:
            base_dir = os.path.dirname(base_output_file)
            base = os.path.splitext(os.path.basename(input_file))[0]
            target_lang_str = "_".join(target_languages)
            base_no_ext = f"{target_lang_str}_{base}"
            final_sentence = start_sentence + len(written_blocks) - 1
            if output_html:
                stitched_html = os.path.join(base_dir, f"{start_sentence}-{final_sentence}_{base_no_ext}.html")
                write_html_file(stitched_html, written_blocks)
            if output_pdf:
                stitched_pdf = os.path.join(base_dir, f"{start_sentence}-{final_sentence}_{base_no_ext}.pdf")
                write_pdf_file(stitched_pdf, written_blocks, target_languages[0])
            stitched_epub = os.path.join(base_dir, f"{start_sentence}-{final_sentence}_{base_no_ext}.epub")
            write_epub_file(stitched_epub, written_blocks, f"Stitched Translation: {start_sentence}-{final_sentence} {base_no_ext}")
            if generate_audio and all_audio_segments:
                stitched_audio = AudioSegment.empty()
                for seg in all_audio_segments:
                    stitched_audio += seg
                stitched_audio_filename = os.path.join(base_dir, f"{start_sentence}-{final_sentence}_{base_no_ext}.mp3")
                stitched_audio.export(stitched_audio_filename, format="mp3", bitrate="320k")
            if generate_video and batch_video_files:
                print("Generating stitched video slide output by concatenating batch video files...")
                concat_list_path = os.path.join(base_dir, f"concat_full_{base_no_ext}.txt")
                with open(concat_list_path, "w", encoding="utf-8") as f:
                    for video_file in batch_video_files:
                        f.write(f"file '{video_file}'\n")
                final_video_path = os.path.join(base_dir, f"{start_sentence}-{final_sentence}_{base_no_ext}_stitched.mp4")
                cmd_concat = [
                    "ffmpeg",
                    "-loglevel", "quiet",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_list_path,
                    "-c", "copy",
                    final_video_path
                ]
                subprocess.run(cmd_concat, check=True)
                os.remove(concat_list_path)
                print(f"Stitched video slide output saved to: {final_video_path}")
        print("\nProcessing complete.")
    except Exception as e:
        print(f"An error occurred: {e}")
