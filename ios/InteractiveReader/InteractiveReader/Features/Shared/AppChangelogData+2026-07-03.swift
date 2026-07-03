extension AppChangelogData {
    static let july3Entries: [AppChangelogEntry] = [
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
