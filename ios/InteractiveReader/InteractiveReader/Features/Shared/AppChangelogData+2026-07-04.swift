extension AppChangelogData {
    static let july4Entries: [AppChangelogEntry] = [
        AppChangelogEntry(
            id: "shared-media-diagnostics-gap-count",
            title: "Media warnings match across surfaces",
            detail: "Playback media diagnostics now include a backend-owned gap count shared by Web Job Detail, Apple playback warning strips, Library media, and offline exports so media-gap warnings stay consistent across surfaces."
        ),
        AppChangelogEntry(
            id: "tvos-music-bed-observed-nonplaying-guard",
            title: "TV playback keeps reading through Music dips",
            detail: "Apple TV Music-bed playback now ignores passive observed-non-playing adoption while the reader is actively narrating, keeping book playback alive and recovering the bed instead of letting a MusicKit status dip stop the sentence track."
        ),
        AppChangelogEntry(
            id: "tvos-sequence-stop-hardening",
            title: "TV playback stop recovery is stronger",
            detail: "Apple TV sequence playback now force-finishes a stuck reader-owned track handoff if tvOS never reports ready or seek completion, and keeps short sentence segments from being over-trimmed during same-track guards."
        ),
        AppChangelogEntry(
            id: "apple-youtube-dub-prepared-subtitle-language",
            title: "Video discovery keeps subtitle language",
            detail: "Apple YouTube Dub now uses prepared subtitle language hints from reviewed video discovery handoffs to set the target language when the user has not edited it, matching Web behavior before the NAS library row refreshes."
        ),
        AppChangelogEntry(
            id: "tvos-sequence-handoff-watchdogs",
            title: "TV handoffs recover themselves",
            detail: "Apple TV sequence handoffs now have reader-owned recovery probes for initial loads, track switches, and same-track dwell seeks, so playback can re-seek and resume when tvOS misses a ready/seek completion instead of leaving the reader muted or stopped."
        ),
        AppChangelogEntry(
            id: "tvos-stale-sequence-transition-recovery",
            title: "TV playback gets unstuck",
            detail: "Apple TV sequence playback now recovers stale initial transitions when sentence audio is already requested and the AVPlayer is ready, preventing the reader from staying muted/transitioning until playback appears to stop."
        ),
        AppChangelogEntry(
            id: "sentence-image-text-collection-helper",
            title: "Image prompts rebuild cleaner",
            detail: "Sentence-image regeneration now shares one ordered chunk-text collection helper for prompt context and batch-range prompts, keeping MyPainter prompt rebuilds easier to audit across Web and Apple playback."
        )
    ]
}
