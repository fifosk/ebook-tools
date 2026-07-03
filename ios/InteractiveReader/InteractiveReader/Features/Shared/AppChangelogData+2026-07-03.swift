extension AppChangelogData {
    static let july3Entries: [AppChangelogEntry] = [
        AppChangelogEntry(
            id: "acquisition-completed-files-safe-metadata",
            title: "Downloader completions are bounded",
            detail: "Download Station poll responses now apply safe manual-download root checks to legacy metadata completion hints too, so Web and Apple Create reconnect only to reviewed local filenames or configured inbox paths."
        ),
        AppChangelogEntry(
            id: "apple-music-bed-manual-pause-skips-stale-filter",
            title: "Music-bed pause stays single-press",
            detail: "Apple TV now treats a manual Apple Music bed pause as an explicit reader pause even during the post-resume stale-event window, keeping one Play/Pause press from stopping only the bed while sentence narration continues."
        ),
        AppChangelogEntry(
            id: "apple-golden-pipeline-music-bed-candidate",
            title: "Golden gate includes Music-bed checks",
            detail: "Golden Apple pipeline verification now runs the serial iPad plus tvOS Music-bed candidate gate after the dogfood pipeline, keeping pause/resume and lookup regressions inside the no-physical-deploy readiness recipe."
        ),
        AppChangelogEntry(
            id: "apple-music-bed-manual-pause-adopts-reader",
            title: "Music-bed pause is unified",
            detail: "When Apple Music is serving as the reading bed, manual or system Music-surface pauses now adopt the reader transport pause path even if Music was already marked manually paused, so one pause intent stops both the bed and sentence narration."
        ),
        AppChangelogEntry(
            id: "apple-music-bed-active-pause-after-echo",
            title: "TV pause keeps both layers together",
            detail: "Apple TV Music-bed pause now keeps the short post-resume echo guard, but after that window a MusicKit pause observed while narration is still requested or playing is mirrored into sentence transport immediately so one press can pause both layers."
        ),
        AppChangelogEntry(
            id: "ipad-music-bed-e2e-bubble-status-split",
            title: "iPad lookup status is separate",
            detail: "The iPad music-bed simulator journey now publishes lookup-bubble counters through a dedicated DEBUG status element, keeping keyboard lookup validation independent from the longer music-bed transport label."
        ),
        AppChangelogEntry(
            id: "apple-music-bed-serial-candidate-gate",
            title: "Music-bed gate checks iPad then TV",
            detail: "The Apple pipeline now exposes a serial Music-bed candidate gate that runs the real iPad keyboard/lookup journey before the real Apple TV remote journey, and the Living Room candidate gate composes it after the shared non-physical pipeline checks."
        ),
        AppChangelogEntry(
            id: "ipad-music-bed-e2e-bubble-status-front",
            title: "iPad lookup test status is steadier",
            detail: "The iPad music-bed simulator journey now publishes lookup-bubble counters at the front of its DEBUG status label, preventing accessibility truncation from hiding bubbleLookup evidence during unattended keyboard validation."
        ),
        AppChangelogEntry(
            id: "apple-tv-music-bed-e2e-observed-pause-retry",
            title: "TV music-bed tests recover probes",
            detail: "The Apple TV music-bed simulator journey now retries its DEBUG observed-pause probe after interactive playback starts, keeping unattended validation from timing out when one delayed simulator callback is missed."
        ),
        AppChangelogEntry(
            id: "apple-music-bed-adopted-pause-fanout",
            title: "One pause fans out to both layers",
            detail: "Apple reader pause adoption now reclaims the Music bed when MusicKit receives the first pause edge, mirrors that adopted pause into Job and Library narration even if the system briefly owns Music, and keeps confirming both layers through the tvOS echo window."
        ),
        AppChangelogEntry(
            id: "apple-music-bed-atomic-pause-confirmation",
            title: "Pause now settles both audio layers",
            detail: "Apple reader pause handling now pauses sentence narration before the Apple Music bed, treats pause confirmation as incomplete while either layer is still active, and settles sequence-mode resume before restoring audio, so iPad and Apple TV no longer need separate presses for bed music and narration."
        ),
        AppChangelogEntry(
            id: "apple-create-provider-label-readiness",
            title: "Create source labels are checked",
            detail: "Apple Create readiness now verifies acquisition provider display labels against the backend label catalog, catching raw provider ids before iPhone, iPad, Apple TV, or Mac iPad-style Create surfaces show them."
        ),
        AppChangelogEntry(
            id: "apple-music-bed-first-press-pause-reinforced",
            title: "First pause reinforces both audio layers",
            detail: "Apple reader pause commands now latch and reinforce the Apple Music bed pause before pausing sentence narration, and pause confirmation retries reapply both sides so tvOS no longer needs a second press when MusicKit receives the first signal."
        ),
        AppChangelogEntry(
            id: "apple-music-bed-single-pause-sync",
            title: "Music-bed pause joins both tracks",
            detail: "Apple reader transport pauses now mute and stop sentence playback before latching the Apple Music bed, reject stale AVPlayer play callbacks after pause, and resume mirrored Music play through the reader transport helper so volume comes back with narration."
        ),
        AppChangelogEntry(
            id: "apple-create-stale-book-provider-message",
            title: "Narrate EPUB source warnings match Web",
            detail: "Apple Narrate EPUB discovery now disables stale template-restored book providers that the backend no longer advertises and shows the same unavailable-on-this-backend guidance and friendly provider labels as Web Create instead of leaving Search enabled."
        ),
        AppChangelogEntry(
            id: "backend-default-sources-friendly-provider-notes",
            title: "Default sources warnings read cleaner",
            detail: "Backend acquisition now formats provider payload labels and partial Default sources provider failures from one shared catalog, using names such as Newznab/Torznab indexers instead of raw ids so Web and Apple Create policy notes stay readable while remaining token-safe."
        )
    ]
}
