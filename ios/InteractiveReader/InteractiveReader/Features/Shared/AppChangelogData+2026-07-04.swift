extension AppChangelogData {
    static let july4Entries: [AppChangelogEntry] = [
        AppChangelogEntry(
            id: "apple-reader-header-dark-glass",
            title: "Reader header stays readable",
            detail: "Apple interactive reader header glass now anchors its panels and pills to a stronger dark translucent base with reduced light material wash, keeping white book metadata and progress chrome legible over dark reader backgrounds even when iPad is in system light mode."
        ),
        AppChangelogEntry(
            id: "apple-single-track-time-jump-anchor",
            title: "Single-track jumps render sooner",
            detail: "Apple reader slider, bookmark, and search-style time jumps now record the selected single-track sentence anchor before audio readiness or cross-batch metadata work begins, keeping rendering pinned to the requested sentence while narration seeks."
        ),
        AppChangelogEntry(
            id: "apple-reader-playback-candidate-gate",
            title: "Reader playback has one local gate",
            detail: "The Apple pipeline now has make verify-apple-reader-playback-candidate for non-deploying reader playback validation: playback Swift contracts plus iPhone, iPad, tvOS simulator, and local Mac iPad-style builds before a physical device test is requested. Changed-test routing selects that gate automatically for reader playback Swift paths while preserving the Music-bed dry-run for Music-sensitive files."
        ),
        AppChangelogEntry(
            id: "apple-sequence-eof-current-lane-guard",
            title: "Reader ignores stale audio endings",
            detail: "Apple sequence playback now advances only when AVPlayer's end callback belongs to the currently active Original or Translation lane, preventing stale detached items from double-advancing, stopping playback, or knocking single-track rendering out of sync."
        ),
        AppChangelogEntry(
            id: "apple-device-deploy-dry-run-matrix",
            title: "Deploy previews cover all default devices",
            detail: "The Apple pipeline now has make apple-device-deploy-dry-run-matrix for no-install default iPad Pro, iPhone, and Living Room TV route previews, plus make apple-device-deploy-readiness-dry-run as a credential-free shared-pipeline app-owned journey that chains host readiness, CoreDevice listing, and those build/install/verify/launch previews before any explicit device deploy."
        ),
        AppChangelogEntry(
            id: "tvos-music-bed-ownership-seeds-reader",
            title: "TV playback keeps reader active",
            detail: "Apple TV and iPad Job/Library playback now keep Apple Music bed ownership synchronized with active narration during startup, lookup-bubble resume, and sentence-transition recovery so one transport action resumes or pauses both layers."
        ),
        AppChangelogEntry(
            id: "tvos-reader-transport-sequence-rearm",
            title: "TV resume keeps sequence playback alive",
            detail: "Apple TV reader playback now re-arms sequence progression after reader-owned pause/resume and reloads the current segment when the tvOS bleed guard detached the audio item, preventing playback from stopping at the next sentence boundary."
        ),
        AppChangelogEntry(
            id: "tvos-active-bed-pause-bit-recovery",
            title: "TV playback survives stale Music pause bits",
            detail: "Apple TV Music-bed playback now treats active reader narration as recoverable even when MusicKit has already marked the bed paused, so passive Apple Music status dips no longer stop the sentence track after startup or resume."
        ),
        AppChangelogEntry(
            id: "tvos-requested-sequence-silent-recovery",
            title: "TV playback recovers requested silence",
            detail: "Apple TV Music-bed playback now keeps probing requested interactive autoplay longer and can restart silent sequence-mode narration when it is not in a real dwell or transition, preventing temporary tvOS/MusicKit handoff dips from becoming a stopped reader."
        ),
        AppChangelogEntry(
            id: "tvos-music-bed-startup-pause-guard",
            title: "TV startup keeps narration alive",
            detail: "Apple TV Music-bed playback now treats requested-but-not-yet-audible narration as active when MusicKit reports an observed non-playing dip, so startup and resume no longer convert that transient bed state into a full reader pause."
        ),
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
