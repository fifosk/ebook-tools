import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

enum PlayerChannelVariant {
    case book
    case subtitles
    case video
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
        coverHeight(isTV: isTV) * 0.68
    }
}

struct PlayerChannelBugView: View {
    let variant: PlayerChannelVariant
    let label: String?

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
                RoundedRectangle(cornerRadius: cornerRadius)
                    .stroke(Color.white.opacity(0.28), lineWidth: 1)
                Image(systemName: iconName)
                    .font(.system(size: iconSize, weight: .semibold))
                    .foregroundStyle(Color.white)
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
        case .youtube:
            colors = [Color(red: 0.94, green: 0.27, blue: 0.27), Color(red: 0.86, green: 0.15, blue: 0.15)]
        case .nas:
            colors = [Color(red: 0.39, green: 0.46, blue: 0.55), Color(red: 0.20, green: 0.25, blue: 0.33)]
        case .dub:
            colors = [Color(red: 0.96, green: 0.25, blue: 0.37), Color(red: 0.66, green: 0.33, blue: 0.97)]
        case .job:
            colors = [Color(red: 0.58, green: 0.64, blue: 0.72), Color(red: 0.28, green: 0.33, blue: 0.41)]
        }
        return LinearGradient(colors: colors, startPoint: .topLeading, endPoint: .bottomTrailing)
    }

    private var logoSize: CGFloat {
        PlayerInfoMetrics.logoSize(isTV: isTV)
    }

    private var iconSize: CGFloat {
        PlayerInfoMetrics.iconSize(isTV: isTV)
    }

    private var cornerRadius: CGFloat {
        PlayerInfoMetrics.cornerRadius(isTV: isTV)
    }

    private var clockFont: Font {
        PlayerInfoMetrics.clockFont(isTV: isTV)
    }

    private var clockHorizontalPadding: CGFloat {
        PlayerInfoMetrics.clockHorizontalPadding(isTV: isTV)
    }

    private var clockVerticalPadding: CGFloat {
        PlayerInfoMetrics.clockVerticalPadding(isTV: isTV)
    }

    private var clockSpacing: CGFloat {
        PlayerInfoMetrics.clockSpacing(isTV: isTV)
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

struct JobTypeGlyph: Equatable {
    let icon: String
    let label: String
}

enum JobTypeGlyphResolver {
    static func glyph(for jobType: String?) -> JobTypeGlyph {
        let normalized = (jobType ?? "").trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        switch normalized {
        case "pipeline", "book":
            return JobTypeGlyph(icon: "📚", label: "Book job")
        case "subtitle", "subtitles", "narrated_subtitle":
            return JobTypeGlyph(icon: "🎞️", label: "Subtitle job")
        case "youtube_dub", "dub":
            return JobTypeGlyph(icon: "🎙️", label: "Dub video job")
        case "video", "youtube":
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
    let accessibilityLabel: String

    var id: String {
        "\(role.rawValue)-\(emoji)"
    }
}

enum LanguageFlagResolver {
    static func resolveFlags(originalLanguage: String?, translationLanguage: String?) -> [LanguageFlagEntry] {
        let originalLabel = resolveLanguageLabel(for: originalLanguage)
        let translationLabel = resolveLanguageLabel(for: translationLanguage)
        return [
            LanguageFlagEntry(
                role: .original,
                emoji: resolveFlag(for: originalLanguage) ?? defaultFlag,
                label: originalLabel,
                accessibilityLabel: "Original language: \(originalLabel)"
            ),
            LanguageFlagEntry(
                role: .translation,
                emoji: resolveFlag(for: translationLanguage) ?? defaultFlag,
                label: translationLabel,
                accessibilityLabel: "Translation language: \(translationLabel)"
            )
        ]
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

struct PlayerLanguageFlagRow: View {
    let flags: [LanguageFlagEntry]
    let isTV: Bool

    var body: some View {
        if !flags.isEmpty {
            HStack(spacing: badgeSpacing) {
                ForEach(Array(orderedFlags.enumerated()), id: \.element.id) { index, flag in
                    LanguageFlagBadge(entry: flag, isTV: isTV, showsLabel: shouldShowLabel)
                    if index < orderedFlags.count - 1 {
                        LanguageConnectorBadge(label: connectorLabel, isTV: isTV)
                    }
                }
            }
        }
    }

    private var badgeSpacing: CGFloat {
        isTV ? 6 : 4
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
        Text(glyph.icon)
            .font(glyphFont)
            .frame(minWidth: 28, alignment: .center)
            .accessibilityLabel(glyph.label)
    }

    private var glyphFont: Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: .caption1).pointSize
        return .system(size: base * 2.0)
        #else
        return .system(size: 28)
        #endif
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

    var body: some View {
        HStack(spacing: showsLabel ? 4 : 0) {
            Text(entry.emoji)
            if showsLabel {
                Text(entry.label)
                    .font(labelFont)
                    .foregroundStyle(Color.white.opacity(0.85))
            }
        }
        .padding(.horizontal, showsLabel ? 6 : 4)
        .padding(.vertical, 3)
        .background(
            Capsule()
                .fill(Color.black.opacity(0.55))
                .overlay(
                    Capsule().stroke(Color.white.opacity(0.22), lineWidth: 1)
                )
        )
        .accessibilityLabel(entry.accessibilityLabel)
    }

    private var labelFont: Font {
        #if os(tvOS)
        return .caption.weight(.semibold)
        #else
        return .caption2.weight(.semibold)
        #endif
    }
}

private struct LanguageConnectorBadge: View {
    let label: String
    let isTV: Bool

    var body: some View {
        Text(label)
            .font(labelFont)
            .foregroundStyle(Color.white.opacity(0.7))
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
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
        return .caption.weight(.semibold)
        #else
        return .caption2.weight(.semibold)
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
