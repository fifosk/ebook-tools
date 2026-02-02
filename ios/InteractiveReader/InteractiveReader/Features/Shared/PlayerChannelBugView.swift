import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

enum MyLinguistPreferences {
    static let lookupLanguageKey = "mylinguist.lookupLanguage"
    static let llmModelKey = "mylinguist.llmModel"
    static let ttsVoiceKey = "mylinguist.ttsVoice"
    static let ttsVoicesByLanguageKey = "mylinguist.ttsVoicesByLanguage"
    static let defaultLookupLanguage = "English"
    static let defaultLlmModel = "ollama_cloud:mistral-large-3:675b-cloud"
}

/// Manager for per-language TTS voice preferences
/// Stores voice selections per language code (e.g., "en" → "Samantha - en-US")
class TtsVoicePreferencesManager {
    static let shared = TtsVoicePreferencesManager()

    private let userDefaults = UserDefaults.standard
    private let storageKey = MyLinguistPreferences.ttsVoicesByLanguageKey

    private init() {}

    /// Get the stored voice for a specific language code
    /// - Parameter languageCode: Normalized language code (e.g., "en", "tr", "hi")
    /// - Returns: The stored voice identifier, or nil if no custom voice is set
    func voice(for languageCode: String) -> String? {
        guard !languageCode.isEmpty else { return nil }
        let normalized = languageCode.lowercased().split(separator: "-").first.map(String.init) ?? languageCode.lowercased()
        let voices = loadVoices()
        return voices[normalized]
    }

    /// Set the voice for a specific language code
    /// - Parameters:
    ///   - voice: The voice identifier to store, or nil to clear
    ///   - languageCode: Normalized language code (e.g., "en", "tr", "hi")
    func setVoice(_ voice: String?, for languageCode: String) {
        guard !languageCode.isEmpty else { return }
        let normalized = languageCode.lowercased().split(separator: "-").first.map(String.init) ?? languageCode.lowercased()
        var voices = loadVoices()

        if let voice, !voice.isEmpty, !isAutoVoice(voice) {
            voices[normalized] = voice
        } else {
            voices.removeValue(forKey: normalized)
        }

        saveVoices(voices)
    }

    /// Clear all custom voice selections, resetting to defaults
    func clearAllVoices() {
        userDefaults.removeObject(forKey: storageKey)
    }

    /// Get all stored voice preferences
    /// - Returns: Dictionary of language code → voice identifier
    func allVoices() -> [String: String] {
        loadVoices()
    }

    /// Check if a voice is an "auto" option that shouldn't be stored
    private func isAutoVoice(_ voice: String) -> Bool {
        let lower = voice.lowercased()
        return lower == "gtts" || lower == "piper-auto" || lower == "macos-auto"
    }

    private func loadVoices() -> [String: String] {
        guard let data = userDefaults.data(forKey: storageKey),
              let voices = try? JSONDecoder().decode([String: String].self, from: data) else {
            return [:]
        }
        return voices
    }

    private func saveVoices(_ voices: [String: String]) {
        guard let data = try? JSONEncoder().encode(voices) else { return }
        userDefaults.set(data, forKey: storageKey)
    }
}

enum PlayerChannelVariant {
    case book
    case subtitles
    case video
    case tv
    case youtube
    case nas
    case dub
    case job
}

enum PlayerInfoMetrics {
    static func logoSize(isTV: Bool) -> CGFloat {
        isTV ? 70 : 47
    }

    static func iconSize(isTV: Bool) -> CGFloat {
        isTV ? 34 : 23
    }

    static func cornerRadius(isTV: Bool) -> CGFloat {
        isTV ? 22 : 16
    }

    static func clockSpacing(isTV: Bool) -> CGFloat {
        isTV ? 6 : 4
    }

    static func clockHorizontalPadding(isTV: Bool) -> CGFloat {
        isTV ? 10 : 7
    }

    static func clockVerticalPadding(isTV: Bool) -> CGFloat {
        isTV ? 6 : 3
    }

    static func clockFont(isTV: Bool) -> Font {
        isTV ? .callout.weight(.bold) : .caption2.weight(.bold)
    }

    static func clockLineHeight(isTV: Bool) -> CGFloat {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .callout : .caption2
        return UIFont.preferredFont(forTextStyle: style).lineHeight
        #else
        return isTV ? 20 : 12
        #endif
    }

    static func badgeHeight(isTV: Bool) -> CGFloat {
        let clockHeight = clockLineHeight(isTV: isTV) + clockVerticalPadding(isTV: isTV) * 2
        return logoSize(isTV: isTV) + clockSpacing(isTV: isTV) + clockHeight
    }

    static func coverHeight(isTV: Bool) -> CGFloat {
        badgeHeight(isTV: isTV)
    }

    static func coverWidth(isTV: Bool) -> CGFloat {
        CoverMetrics.bookWidth(forHeight: coverHeight(isTV: isTV))
    }
}

struct PlayerChannelBugView: View {
    let variant: PlayerChannelVariant
    let label: String?
    let sizeScale: CGFloat

    init(variant: PlayerChannelVariant, label: String?, sizeScale: CGFloat = 1.0) {
        self.variant = variant
        self.label = label
        self.sizeScale = sizeScale
    }

    private static let hourFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH"
        return formatter
    }()

    private static let minuteFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "mm"
        return formatter
    }()

    var body: some View {
        VStack(spacing: clockSpacing) {
            ZStack {
                RoundedRectangle(cornerRadius: cornerRadius)
                    .fill(gradient)
                if variant == .youtube {
                    youtubeLogo
                } else if variant == .tv {
                    tubeTvLogo
                } else {
                    Image(systemName: iconName)
                        .font(.system(size: iconSize, weight: .semibold))
                        .foregroundStyle(Color.white)
                }
                RoundedRectangle(cornerRadius: cornerRadius)
                    .stroke(Color.white.opacity(0.28), lineWidth: 1)
            }
            .frame(width: logoSize, height: logoSize)
            .shadow(color: Color.black.opacity(0.35), radius: 8, x: 0, y: 6)

            TimelineView(.periodic(from: .now, by: 1)) { context in
                let hour = Self.hourFormatter.string(from: context.date)
                let minute = Self.minuteFormatter.string(from: context.date)
                let seconds = Calendar.current.component(.second, from: context.date)
                let blink = seconds % 2 == 0
                HStack(spacing: 0) {
                    Text(hour)
                    Text(":")
                        .opacity(blink ? 1 : 0)
                    Text(minute)
                }
                .font(clockFont)
                .monospacedDigit()
                .foregroundStyle(Color.white)
                .padding(.horizontal, clockHorizontalPadding)
                .padding(.vertical, clockVerticalPadding)
                .background(
                    Capsule()
                        .fill(Color.black.opacity(0.85))
                        .overlay(Capsule().stroke(Color.white.opacity(0.2), lineWidth: 1))
                )
            }
        }
        .accessibilityLabel(label ?? "Job")
        .accessibilityHidden(true)
    }

    private var iconName: String {
        switch variant {
        case .book:
            return "book.closed"
        case .subtitles:
            return "captions.bubble"
        case .video, .youtube:
            return "play.rectangle"
        case .tv:
            return "tv"
        case .nas:
            return "tray.2"
        case .dub:
            return "waveform"
        case .job:
            return "briefcase"
        }
    }

    private var gradient: LinearGradient {
        let colors: [Color]
        switch variant {
        case .book:
            colors = [Color(red: 0.96, green: 0.62, blue: 0.04), Color(red: 0.98, green: 0.45, blue: 0.09)]
        case .subtitles:
            colors = [Color(red: 0.39, green: 0.40, blue: 0.95), Color(red: 0.22, green: 0.74, blue: 0.97)]
        case .video:
            colors = [Color(red: 0.13, green: 0.77, blue: 0.37), Color(red: 0.08, green: 0.72, blue: 0.65)]
        case .tv:
            colors = [Color(red: 0.06, green: 0.45, blue: 0.56), Color(red: 0.02, green: 0.62, blue: 0.78)]
        case .youtube:
            colors = [Color(red: 0.06, green: 0.09, blue: 0.16), Color(red: 0.01, green: 0.02, blue: 0.09)]
        case .nas:
            colors = [Color(red: 0.39, green: 0.46, blue: 0.55), Color(red: 0.20, green: 0.25, blue: 0.33)]
        case .dub:
            colors = [Color(red: 0.96, green: 0.25, blue: 0.37), Color(red: 0.66, green: 0.33, blue: 0.97)]
        case .job:
            colors = [Color(red: 0.58, green: 0.64, blue: 0.72), Color(red: 0.28, green: 0.33, blue: 0.41)]
        }
        return LinearGradient(colors: colors, startPoint: .topLeading, endPoint: .bottomTrailing)
    }

    private var youtubeLogo: some View {
        let markWidth = logoSize * 0.8
        let markHeight = logoSize * 0.52
        let cornerRadius = markHeight * 0.28
        return ZStack {
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .fill(Color(red: 1, green: 0, blue: 0))
                .frame(width: markWidth, height: markHeight)
            PlayTriangle()
                .fill(Color.white)
                .frame(width: markHeight * 0.45, height: markHeight * 0.45)
                .offset(x: markHeight * 0.04)
        }
    }

    private var tubeTvLogo: some View {
        let markWidth = logoSize * 0.74
        let markHeight = logoSize * 0.62
        return TubeTVGlyphMark(width: markWidth, height: markHeight, color: .white)
    }

    private var logoSize: CGFloat {
        PlayerInfoMetrics.logoSize(isTV: isTV) * sizeScale
    }

    private var iconSize: CGFloat {
        PlayerInfoMetrics.iconSize(isTV: isTV) * sizeScale
    }

    private var cornerRadius: CGFloat {
        PlayerInfoMetrics.cornerRadius(isTV: isTV) * sizeScale
    }

    private var clockFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .callout : .caption2
        let baseSize = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: baseSize * sizeScale, weight: .bold)
        #else
        let baseSize: CGFloat = isTV ? 16 : 11
        return .system(size: baseSize * sizeScale, weight: .bold)
        #endif
    }

    private var clockHorizontalPadding: CGFloat {
        PlayerInfoMetrics.clockHorizontalPadding(isTV: isTV) * sizeScale
    }

    private var clockVerticalPadding: CGFloat {
        PlayerInfoMetrics.clockVerticalPadding(isTV: isTV) * sizeScale
    }

    private var clockSpacing: CGFloat {
        PlayerInfoMetrics.clockSpacing(isTV: isTV) * sizeScale
    }

    private var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }
}

private struct PlayTriangle: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.minX, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.midY))
        path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY))
        path.closeSubpath()
        return path
    }
}

private struct YoutubeGlyphMark: View {
    let width: CGFloat
    let height: CGFloat

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: height * 0.28, style: .continuous)
                .fill(Color(red: 1, green: 0, blue: 0))
            PlayTriangle()
                .fill(Color.white)
                .frame(width: height * 0.42, height: height * 0.42)
                .offset(x: height * 0.04)
        }
        .frame(width: width, height: height)
    }
}

private struct TubeTVGlyphMark: View {
    let width: CGFloat
    let height: CGFloat
    let color: Color

    var body: some View {
        TubeTVShape()
            .stroke(
                color,
                style: StrokeStyle(
                    lineWidth: max(1.2, height * 0.12),
                    lineCap: .round,
                    lineJoin: .round
                )
            )
            .frame(width: width, height: height)
    }
}

private struct TubeTVShape: Shape {
    func path(in rect: CGRect) -> Path {
        let width = rect.width
        let height = rect.height
        let bodyRect = CGRect(
            x: rect.minX + width * 0.05,
            y: rect.minY + height * 0.18,
            width: width * 0.9,
            height: height * 0.62
        )
        let screenRect = bodyRect.insetBy(dx: bodyRect.width * 0.18, dy: bodyRect.height * 0.2)
        let antennaHeight = height * 0.2
        let baseY = bodyRect.maxY + height * 0.08
        let baseHalf = width * 0.18
        let antennaSpan = width * 0.2

        var path = Path()
        path.addRoundedRect(in: bodyRect, cornerSize: CGSize(width: bodyRect.height * 0.22, height: bodyRect.height * 0.22))
        path.addRoundedRect(in: screenRect, cornerSize: CGSize(width: screenRect.height * 0.18, height: screenRect.height * 0.18))
        path.move(to: CGPoint(x: bodyRect.midX, y: bodyRect.minY))
        path.addLine(to: CGPoint(x: bodyRect.midX - antennaSpan, y: bodyRect.minY - antennaHeight))
        path.move(to: CGPoint(x: bodyRect.midX, y: bodyRect.minY))
        path.addLine(to: CGPoint(x: bodyRect.midX + antennaSpan, y: bodyRect.minY - antennaHeight))
        path.move(to: CGPoint(x: bodyRect.midX - baseHalf, y: baseY))
        path.addLine(to: CGPoint(x: bodyRect.midX + baseHalf, y: baseY))
        return path
    }
}

enum LanguageFlagRole: String {
    case original
    case translation
}

struct JobTypeGlyph: Equatable {
    let icon: String
    let label: String
    let variant: PlayerChannelVariant?

    init(icon: String, label: String, variant: PlayerChannelVariant? = nil) {
        self.icon = icon
        self.label = label
        self.variant = variant
    }
}

enum JobTypeGlyphResolver {
    static func glyph(for jobType: String?) -> JobTypeGlyph {
        let normalized = (jobType ?? "").trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if normalized.contains("youtube") {
            let label = normalized.contains("dub") ? "YouTube dub job" : "YouTube job"
            return JobTypeGlyph(icon: "YT", label: label, variant: .youtube)
        }
        switch normalized {
        case "pipeline", "book":
            return JobTypeGlyph(icon: "📚", label: "Book job")
        case "subtitle", "subtitles", "narrated_subtitle":
            return JobTypeGlyph(icon: "🎞️", label: "Subtitle job")
        case "dub":
            return JobTypeGlyph(icon: "🎙️", label: "Dub video job")
        case "video":
            return JobTypeGlyph(icon: "🎞️", label: "Video job")
        default:
            let label = normalized.isEmpty ? "Job" : "\(normalized) job"
            return JobTypeGlyph(icon: "📦", label: label)
        }
    }
}

struct LanguageFlagEntry: Identifiable, Equatable {
    let role: LanguageFlagRole
    let emoji: String
    let label: String
    let shortLabel: String
    let accessibilityLabel: String

    var id: String {
        "\(role.rawValue)-\(emoji)"
    }
}

enum LanguageFlagResolver {
    static func resolveFlags(originalLanguage: String?, translationLanguage: String?) -> [LanguageFlagEntry] {
        let originalLabel = resolveLanguageLabel(for: originalLanguage)
        let translationLabel = resolveLanguageLabel(for: translationLanguage)
        let originalCode = resolveLanguageShortCode(for: originalLanguage) ?? originalLabel
        let translationCode = resolveLanguageShortCode(for: translationLanguage) ?? translationLabel
        return [
            LanguageFlagEntry(
                role: .original,
                emoji: resolveFlag(for: originalLanguage) ?? defaultFlag,
                label: originalLabel,
                shortLabel: originalCode,
                accessibilityLabel: "Original language: \(originalLabel)"
            ),
            LanguageFlagEntry(
                role: .translation,
                emoji: resolveFlag(for: translationLanguage) ?? defaultFlag,
                label: translationLabel,
                shortLabel: translationCode,
                accessibilityLabel: "Translation language: \(translationLabel)"
            )
        ]
    }

    static func flagEntry(for language: String?, role: LanguageFlagRole = .translation) -> LanguageFlagEntry {
        let label = resolveLanguageLabel(for: language)
        let shortLabel = resolveLanguageShortCode(for: language) ?? label
        return LanguageFlagEntry(
            role: role,
            emoji: resolveFlag(for: language) ?? defaultFlag,
            label: label,
            shortLabel: shortLabel,
            accessibilityLabel: label
        )
    }

    static func availableLanguageLabels() -> [String] {
        let unique = Set(languageNameMap.values)
        return unique.sorted { left, right in
            left.localizedCaseInsensitiveCompare(right) == .orderedAscending
        }
    }

    private static func resolveFlag(for language: String?) -> String? {
        guard let language, !language.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return nil
        }
        let resolved = resolveLanguageCode(language) ?? language
        let normalized = normalizeFlagKey(resolved)
        if normalized.contains("-"),
           let region = regionFromCode(normalized),
           let flag = flagEmoji(forRegion: region) {
            return flag
        }
        if let region = languageRegionMap[normalized], let flag = flagEmoji(forRegion: region) {
            return flag
        }
        if let base = normalized.split(separator: "-").first,
           let region = languageRegionMap[String(base)],
           let flag = flagEmoji(forRegion: region) {
            return flag
        }
        return nil
    }

    private static func resolveLanguageCode(_ language: String) -> String? {
        let trimmed = language.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        if let direct = languageCodes[trimmed] {
            return direct
        }

        let normalized = trimmed.lowercased().replacingOccurrences(of: "_", with: "-")
        if let alias = languageCodeAliases[normalized] {
            return alias
        }

        if let matched = languageCodes.first(where: { $0.key.lowercased() == normalized })?.value {
            return matched
        }

        if normalized.range(of: "^[a-z]{2,3}(-[a-z]{2,3})?$", options: .regularExpression) != nil {
            return normalized
        }

        return nil
    }

    private static func resolveLanguageLabel(for language: String?) -> String {
        let trimmed = language?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !trimmed.isEmpty else { return "Unknown" }

        if languageCodes[trimmed] != nil {
            return trimmed
        }

        let code = (resolveLanguageCode(trimmed) ?? trimmed)
            .lowercased()
            .replacingOccurrences(of: "_", with: "-")
        if let name = languageNameMap[code] {
            return name
        }
        if let base = code.split(separator: "-").first,
           let name = languageNameMap[String(base)] {
            return name
        }
        return trimmed
    }

    private static func resolveLanguageShortCode(for language: String?) -> String? {
        let trimmed = language?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !trimmed.isEmpty else { return nil }
        let resolved = resolveLanguageCode(trimmed) ?? trimmed
        let normalized = resolved
            .lowercased()
            .replacingOccurrences(of: "_", with: "-")
        guard !normalized.isEmpty else { return nil }
        return normalized
            .split(separator: "-")
            .map { $0.uppercased() }
            .joined(separator: "-")
    }

    private static func normalizeFlagKey(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased().replacingOccurrences(of: "_", with: "-")
    }

    private static func regionFromCode(_ value: String) -> String? {
        let parts = value.split(separator: "-")
        guard parts.count > 1, let last = parts.last, last.count == 2 else { return nil }
        return last.uppercased()
    }

    private static func flagEmoji(forRegion region: String) -> String? {
        let upper = region.uppercased()
        guard upper.count == 2 else { return nil }
        var scalars: [UnicodeScalar] = []
        for scalar in upper.unicodeScalars {
            guard let flagScalar = UnicodeScalar(127397 + scalar.value) else { return nil }
            scalars.append(flagScalar)
        }
        return String(String.UnicodeScalarView(scalars))
    }

    private static let defaultFlag: String = {
        guard let scalar = UnicodeScalar(0x1F310) else { return "" }
        return String(scalar)
    }()

    private static let languageCodes: [String: String] = [
        "Afrikaans": "af",
        "Albanian": "sq",
        "Arabic": "ar",
        "Amharic": "am",
        "Armenian": "hy",
        "Basque": "eu",
        "Belarusian": "be",
        "Bengali": "bn",
        "Bulgarian": "bg",
        "Bosnian": "bs",
        "Burmese": "my",
        "Catalan": "ca",
        "Kazakh": "kk",
        "Kyrgyz": "ky",
        "Mongolian": "mn",
        "Tajik": "tg",
        "Turkmen": "tk",
        "Uzbek": "uz",
        "Chinese (Simplified)": "zh-CN",
        "Chinese (Traditional)": "zh-TW",
        "Czech": "cs",
        "Croatian": "hr",
        "Danish": "da",
        "Dutch": "nl",
        "English": "en",
        "Esperanto": "eo",
        "Estonian": "et",
        "Faroese": "fo",
        "Filipino": "tl",
        "Finnish": "fi",
        "French": "fr",
        "German": "de",
        "Georgian": "ka",
        "Greek": "el",
        "Gujarati": "gu",
        "Hausa": "ha",
        "Hebrew": "he",
        "Hindi": "hi",
        "Hungarian": "hu",
        "Irish": "ga",
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
        "Lithuanian": "lt",
        "Luxembourgish": "lb",
        "Macedonian": "mk",
        "Malay": "ms",
        "Malayalam": "ml",
        "Maltese": "mt",
        "Marathi": "mr",
        "Nepali": "ne",
        "Norwegian": "no",
        "Pashto": "ps",
        "Polish": "pl",
        "Portuguese": "pt",
        "Punjabi": "pa",
        "Scots": "sco",
        "Scottish Gaelic": "gd",
        "Galician": "gl",
        "Romani": "rom",
        "Spanish": "es",
        "Romanian": "ro",
        "Russian": "ru",
        "Sinhala": "si",
        "Slovak": "sk",
        "Slovenian": "sl",
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
    ]

    private static let languageCodeAliases: [String: String] = [
        "amh": "am",
        "ara": "ar",
        "ben": "bn",
        "bos": "bs",
        "bul": "bg",
        "ces": "cs",
        "chi": "zh-cn",
        "chs": "zh-cn",
        "cht": "zh-tw",
        "cmn": "zh-cn",
        "cze": "cs",
        "dan": "da",
        "deu": "de",
        "dut": "nl",
        "ell": "el",
        "eng": "en",
        "est": "et",
        "fas": "fa",
        "fin": "fi",
        "fre": "fr",
        "fra": "fr",
        "ger": "de",
        "gre": "el",
        "heb": "he",
        "hin": "hi",
        "hrv": "hr",
        "hun": "hu",
        "ind": "id",
        "ita": "it",
        "jpn": "ja",
        "kor": "ko",
        "lav": "lv",
        "lit": "lt",
        "may": "ms",
        "msa": "ms",
        "nor": "no",
        "pes": "fa",
        "per": "fa",
        "pol": "pl",
        "por": "pt",
        "por-br": "pt-br",
        "ptbr": "pt-br",
        "pus": "ps",
        "ron": "ro",
        "rum": "ro",
        "rus": "ru",
        "slo": "sk",
        "slk": "sk",
        "slv": "sl",
        "spa": "es",
        "srp": "sr",
        "swe": "sv",
        "tam": "ta",
        "tel": "te",
        "tha": "th",
        "tur": "tr",
        "ukr": "uk",
        "vie": "vi",
        "zho": "zh-cn"
    ]

    private static let languageNameMap: [String: String] = {
        var map: [String: String] = [:]
        for (name, code) in languageCodes {
            map[code.lowercased()] = name
        }
        return map
    }()

    private static let languageRegionMap: [String: String] = [
        "af": "ZA",
        "am": "ET",
        "ar": "SA",
        "be": "BY",
        "bg": "BG",
        "bn": "BD",
        "bs": "BA",
        "ca": "ES",
        "cs": "CZ",
        "cy": "GB",
        "da": "DK",
        "de": "DE",
        "el": "GR",
        "en": "US",
        "en-gb": "GB",
        "en-us": "US",
        "es": "ES",
        "et": "EE",
        "eu": "ES",
        "fa": "IR",
        "fi": "FI",
        "fil": "PH",
        "fo": "FO",
        "fr": "FR",
        "ga": "IE",
        "gd": "GB",
        "gl": "ES",
        "gu": "IN",
        "ha": "NG",
        "he": "IL",
        "hi": "IN",
        "hr": "HR",
        "hu": "HU",
        "hy": "AM",
        "id": "ID",
        "is": "IS",
        "it": "IT",
        "ja": "JP",
        "jw": "ID",
        "ka": "GE",
        "kk": "KZ",
        "km": "KH",
        "kn": "IN",
        "ko": "KR",
        "ky": "KG",
        "la": "VA",
        "lb": "LU",
        "lt": "LT",
        "lv": "LV",
        "mk": "MK",
        "ml": "IN",
        "mn": "MN",
        "mr": "IN",
        "ms": "MY",
        "mt": "MT",
        "my": "MM",
        "ne": "NP",
        "nl": "NL",
        "no": "NO",
        "pa": "IN",
        "pl": "PL",
        "ps": "AF",
        "pt": "PT",
        "pt-br": "BR",
        "ro": "RO",
        "ru": "RU",
        "sco": "GB",
        "si": "LK",
        "sk": "SK",
        "sl": "SI",
        "sq": "AL",
        "sr": "RS",
        "su": "ID",
        "sv": "SE",
        "sw": "KE",
        "ta": "IN",
        "te": "IN",
        "tg": "TJ",
        "th": "TH",
        "tl": "PH",
        "tr": "TR",
        "uk": "UA",
        "ur": "PK",
        "uz": "UZ",
        "vi": "VN",
        "xh": "ZA",
        "yo": "NG",
        "zh": "CN",
        "zh-cn": "CN",
        "zh-tw": "TW",
        "zu": "ZA"
    ]
}

#if os(tvOS)
struct TVLanguageFlagButtonStyle: ButtonStyle {
    @Environment(\.isFocused) var isFocused

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.95 : (isFocused ? 1.1 : 1.0))
            .brightness(isFocused ? 0.15 : 0)
            .animation(.easeInOut(duration: 0.15), value: isFocused)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}
#endif

struct PlayerLanguageFlagRow: View {
    let flags: [LanguageFlagEntry]
    let modelLabel: String?
    let isTV: Bool
    let sizeScale: CGFloat
    let activeRoles: Set<LanguageFlagRole>
    let availableRoles: Set<LanguageFlagRole>
    let onToggleRole: ((LanguageFlagRole) -> Void)?
    let showConnector: Bool

    init(
        flags: [LanguageFlagEntry],
        modelLabel: String?,
        isTV: Bool,
        sizeScale: CGFloat = 1.0,
        activeRoles: Set<LanguageFlagRole> = [],
        availableRoles: Set<LanguageFlagRole> = [.original, .translation],
        onToggleRole: ((LanguageFlagRole) -> Void)? = nil,
        showConnector: Bool = true
    ) {
        self.flags = flags
        self.modelLabel = modelLabel
        self.isTV = isTV
        self.sizeScale = sizeScale
        self.activeRoles = activeRoles
        self.availableRoles = availableRoles
        self.onToggleRole = onToggleRole
        self.showConnector = showConnector
    }

    var body: some View {
        if !flags.isEmpty {
            HStack(spacing: badgeSpacing) {
                ForEach(Array(orderedFlags.enumerated()), id: \.element.id) { index, flag in
                    let role = flag.role
                    let isAvailable = availableRoles.contains(role)
                    let badge = LanguageFlagBadge(
                        entry: flag,
                        isTV: isTV,
                        showsLabel: shouldShowLabel,
                        sizeScale: sizeScale
                    )
                    .opacity(flagOpacity(isAvailable: isAvailable, role: role))
                    if let onToggleRole, isAvailable {
                        Button(action: { onToggleRole(role) }) {
                            badge
                        }
                        #if os(tvOS)
                        .buttonStyle(TVLanguageFlagButtonStyle())
                        #else
                        .buttonStyle(.plain)
                        #endif
                    } else {
                        badge
                    }
                    if index < orderedFlags.count - 1, showConnector {
                        LanguageConnectorBadge(label: connectorLabel, isTV: isTV, sizeScale: sizeScale)
                    }
                }
                if let modelBadgeLabel {
                    LanguageModelBadge(label: modelBadgeLabel, isTV: isTV, sizeScale: sizeScale)
                }
            }
        }
    }

    private var badgeSpacing: CGFloat {
        (isTV ? 6 : 4) * sizeScale
    }

    private func flagOpacity(isAvailable: Bool, role: LanguageFlagRole) -> Double {
        guard isAvailable else { return 0.3 }
        guard !activeRoles.isEmpty else { return 1.0 }
        return activeRoles.contains(role) ? 1.0 : 0.55
    }

    private var orderedFlags: [LanguageFlagEntry] {
        let original = flags.first(where: { $0.role == .original })
        let translation = flags.first(where: { $0.role == .translation })
        if let original, let translation {
            return [original, translation]
        }
        return flags
    }

    private var connectorLabel: String {
        "to"
    }

    private var modelBadgeLabel: String? {
        guard let modelLabel = modelLabel?.trimmingCharacters(in: .whitespacesAndNewlines),
              !modelLabel.isEmpty else {
            return nil
        }
        return "using [\(modelLabel)]"
    }

    private var shouldShowLabel: Bool {
        isTV || isPad
    }

    private var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }
}

struct JobTypeGlyphBadge: View {
    let glyph: JobTypeGlyph

    var body: some View {
        Group {
            if glyph.variant == .youtube {
                YoutubeGlyphMark(width: youtubeWidth, height: youtubeHeight)
            } else if glyph.variant == .tv {
                TubeTVGlyphMark(width: tubeTvWidth, height: tubeTvHeight, color: .primary)
            } else {
                Text(glyph.icon)
                    .font(glyphFont)
            }
        }
        .frame(minWidth: 28, alignment: .center)
        .accessibilityLabel(glyph.label)
    }

    private var youtubeHeight: CGFloat {
        glyphPointSize * 0.7
    }

    private var youtubeWidth: CGFloat {
        youtubeHeight * 1.6
    }

    private var tubeTvHeight: CGFloat {
        glyphPointSize * 0.7
    }

    private var tubeTvWidth: CGFloat {
        tubeTvHeight * 1.3
    }

    private var glyphPointSize: CGFloat {
        #if os(iOS) || os(tvOS)
        return UIFont.preferredFont(forTextStyle: .caption1).pointSize * 2.0
        #else
        return 28
        #endif
    }

    private var glyphFont: Font {
        .system(size: glyphPointSize)
    }
}

struct LanguageFlagPairView: View {
    let flags: [LanguageFlagEntry]

    var body: some View {
        let ordered = orderedFlags
        if let first = ordered.first {
            HStack(spacing: 6) {
                Text(first.emoji)
                    .font(flagFont)
                if let second = ordered.dropFirst().first {
                    Text("-")
                        .font(connectorFont)
                        .foregroundStyle(.secondary)
                    Text(second.emoji)
                        .font(flagFont)
                }
            }
            .accessibilityLabel(accessibilityLabel(for: ordered))
        }
    }

    private var orderedFlags: [LanguageFlagEntry] {
        let original = flags.first(where: { $0.role == .original })
        let translation = flags.first(where: { $0.role == .translation })
        if let original, let translation {
            return [original, translation]
        }
        return flags
    }

    private func accessibilityLabel(for flags: [LanguageFlagEntry]) -> String {
        guard let first = flags.first else { return "Languages" }
        if let second = flags.dropFirst().first {
            return "\(first.label) to \(second.label)"
        }
        return first.label
    }

    private var flagFont: Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: .caption1).pointSize
        return .system(size: base * 2.0)
        #else
        return .system(size: 28)
        #endif
    }

    private var connectorFont: Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: .caption1).pointSize
        return .system(size: base)
        #else
        return .system(size: 14)
        #endif
    }
}

private struct LanguageFlagBadge: View {
    let entry: LanguageFlagEntry
    let isTV: Bool
    let showsLabel: Bool
    let sizeScale: CGFloat

    var body: some View {
        HStack(spacing: labelSpacing) {
            Text(entry.emoji)
                .font(emojiFont)
            if showsLabel {
                Text(entry.shortLabel.isEmpty ? entry.label : entry.shortLabel)
                    .font(labelFont)
                    .foregroundStyle(Color.white.opacity(0.85))
            }
        }
        .padding(.horizontal, labelPaddingHorizontal)
        .padding(.vertical, labelPaddingVertical)
        .background(
            Capsule()
                .fill(Color.black.opacity(0.55))
                .overlay(
                    Capsule().stroke(Color.white.opacity(0.22), lineWidth: 1)
                )
        )
        .accessibilityLabel(entry.accessibilityLabel)
    }

    private var labelSpacing: CGFloat {
        (showsLabel ? 4 : 0) * sizeScale
    }

    private var labelPaddingHorizontal: CGFloat {
        (showsLabel ? 6 : 5) * sizeScale
    }

    private var labelPaddingVertical: CGFloat {
        (showsLabel ? 3 : 3) * sizeScale
    }

    private var labelFont: Font {
        #if os(tvOS)
        return scaledFont(style: .caption1, weight: .semibold)
        #else
        return scaledFont(style: .caption2, weight: .semibold)
        #endif
    }

    private var emojiFont: Font {
        #if os(tvOS)
        return scaledFont(style: .caption1, weight: .semibold)
        #else
        return scaledFont(style: .caption1, weight: .semibold)
        #endif
    }

    private func scaledFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * sizeScale, weight: weight)
        #else
        return .system(size: 12 * sizeScale, weight: weight)
        #endif
    }
}

private struct LanguageConnectorBadge: View {
    let label: String
    let isTV: Bool
    let sizeScale: CGFloat

    var body: some View {
        Text(label)
            .font(labelFont)
            .foregroundStyle(Color.white.opacity(0.7))
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .padding(.horizontal, 6 * sizeScale)
            .padding(.vertical, 2 * sizeScale)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.45))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.16), lineWidth: 1)
                    )
            )
            .accessibilityLabel(label)
    }

    private var labelFont: Font {
        #if os(tvOS)
        return scaledFont(style: .caption1, weight: .semibold)
        #else
        return scaledFont(style: .caption2, weight: .semibold)
        #endif
    }

    private func scaledFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * sizeScale, weight: weight)
        #else
        return .system(size: 12 * sizeScale, weight: weight)
        #endif
    }
}

private struct LanguageModelBadge: View {
    let label: String
    let isTV: Bool
    let sizeScale: CGFloat

    var body: some View {
        Text(label)
            .font(labelFont)
            .foregroundStyle(Color.white.opacity(0.7))
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .padding(.horizontal, 8 * sizeScale)
            .padding(.vertical, 3 * sizeScale)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.55))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.2), lineWidth: 1)
                    )
            )
            .accessibilityLabel(label)
    }

    private var labelFont: Font {
        #if os(tvOS)
        return scaledFont(style: .caption1, weight: .semibold)
        #else
        return scaledFont(style: .caption2, weight: .semibold)
        #endif
    }

    private func scaledFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * sizeScale, weight: weight)
        #else
        return .system(size: 12 * sizeScale, weight: weight)
        #endif
    }
}

struct PlayerCoverStackView: View {
    let primaryURL: URL?
    let secondaryURL: URL?
    let width: CGFloat
    let height: CGFloat
    let isTV: Bool

    var body: some View {
        if let resolvedPrimary = primaryURL ?? secondaryURL {
            let resolvedSecondary = (primaryURL != nil && secondaryURL != nil && primaryURL != secondaryURL)
                ? secondaryURL
                : nil
            ZStack(alignment: .topLeading) {
                coverImage(url: resolvedPrimary, width: width, height: height)
                if let resolvedSecondary {
                    coverImage(url: resolvedSecondary, width: secondaryWidth, height: secondaryHeight)
                        .offset(x: secondaryOffset, y: secondaryYOffset)
                }
            }
            .frame(width: stackWidth(resolvedSecondary != nil), height: height, alignment: .leading)
        }
    }

    private func coverImage(url: URL, width: CGFloat, height: CGFloat) -> some View {
        AsyncImage(url: url) { phase in
            if let image = phase.image {
                image.resizable().scaledToFill()
            } else {
                Color.black.opacity(0.35)
            }
        }
        .frame(width: width, height: height)
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .stroke(Color.white.opacity(0.22), lineWidth: 1)
        )
    }

    private var secondaryScale: CGFloat {
        0.66
    }

    private var secondaryWidth: CGFloat {
        width * secondaryScale
    }

    private var secondaryHeight: CGFloat {
        height * secondaryScale
    }

    private var secondaryOffset: CGFloat {
        width * (isTV ? 0.72 : 0.68)
    }

    private var secondaryYOffset: CGFloat {
        height * (1 - secondaryScale)
    }

    private func stackWidth(_ hasSecondary: Bool) -> CGFloat {
        width + (hasSecondary ? secondaryOffset : 0)
    }
}
