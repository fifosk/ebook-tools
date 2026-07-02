extension AppChangelogData {
    static let july3Entries: [AppChangelogEntry] = [
        AppChangelogEntry(
            id: "apple-music-bed-single-pause-sync",
            title: "Music-bed pause joins both tracks",
            detail: "Apple reader transport pauses now mute and stop sentence playback before latching the Apple Music bed, reject stale AVPlayer play callbacks after pause, and resume mirrored Music play through the reader transport helper so volume comes back with narration."
        )
    ]
}
