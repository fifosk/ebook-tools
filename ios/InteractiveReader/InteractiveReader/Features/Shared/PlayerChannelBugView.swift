import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

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
        return YoutubeGlyphMark(width: markWidth, height: markHeight)
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

enum LanguageFlagRole: String {
    case original
    case translation
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
