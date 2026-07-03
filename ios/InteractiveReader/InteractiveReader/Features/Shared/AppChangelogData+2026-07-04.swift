extension AppChangelogData {
    static let july4Entries: [AppChangelogEntry] = [
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
