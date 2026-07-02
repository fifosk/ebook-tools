extension AppChangelogData {
    static let july3Entries: [AppChangelogEntry] = [
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
