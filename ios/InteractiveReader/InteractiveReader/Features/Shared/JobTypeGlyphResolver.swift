import Foundation

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
