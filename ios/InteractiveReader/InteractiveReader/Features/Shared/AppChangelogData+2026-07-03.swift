extension AppChangelogData {
    static let july3Entries: [AppChangelogEntry] = [
        AppChangelogEntry(
            id: "tvos-sequence-dwell-pins-before-boundary",
            title: "TV handoffs avoid next-sentence slivers",
            detail: "Interactive reader sequence dwell now pins muted playback just before the sentence boundary and uses the same early boundary for fallback checks, reducing cases where Apple TV can leak a tiny piece of the next original sentence before switching to the translation track."
        ),
        AppChangelogEntry(
            id: "acquisition-defaults-overfill-policy",
            title: "Discovery overfill rules are explicit",
            detail: "Backend acquisition planning now names the Default sources rule that only local NAS/manual providers may overfill visible result slots, keeping optional remote searches slot-bound for Web and Apple Create."
        ),
        AppChangelogEntry(
            id: "acquisition-defaults-skip-filled-remotes",
            title: "Default discovery avoids extra remotes",
            detail: "Backend acquisition tests now pin that Web and Apple Create Default sources skip optional YouTube or indexer searches once local NAS/manual candidates fill the visible result limit."
        ),
        AppChangelogEntry(
            id: "apple-reader-repro-log-fresh-window",
            title: "Reader repro logs stay fresh",
            detail: "The combined Apple playback reader-repro helper now verifies pause/resume and resume-offset evidence against the fresh pulled log suffix, matching the single-purpose transport checks."
        ),
        AppChangelogEntry(
            id: "apple-playback-log-fresh-window",
            title: "Device playback logs verify fresh repros",
            detail: "Apple playback-log pull-and-verify now preserves the previous local device log and checks only the fresh suffix, so old Living Room or Cinema failures no longer mask the current hardware repro."
        ),
        AppChangelogEntry(
            id: "tvos-sequence-handoff-tail-trim",
            title: "TV track switches trim audio bleed",
            detail: "Apple TV interactive reader sequence playback now mutes and fades sentence boundaries earlier and ignores stale fade work after an AVPlayer item changes, reducing cut-short next-sentence audio before the translation track starts."
        ),
        AppChangelogEntry(
            id: "tvos-autoplay-audio-state-flood-guard",
            title: "TV playback stops retry floods",
            detail: "Apple TV Job and Library playback no longer let rapid audio-state pulses repeatedly restart pending interactive autoplay while the Apple Music bed is pausing, preventing Living Room sessions from looping on one sentence."
        ),
        AppChangelogEntry(
            id: "tvos-paused-reader-cancels-autoplay-retry",
            title: "TV paused readers stop retrying",
            detail: "Apple TV Job and Library playback now cancels pending interactive autoplay retries whenever the reader-owned Apple Music bed is paused, preventing Living Room sessions from looping on the same sentence with no playback."
        ),
        AppChangelogEntry(
            id: "tvos-music-bed-autoplay-stale-pause-guard",
            title: "TV autoplay avoids Music-bed loops",
            detail: "Apple TV Job and Library playback now treat pending interactive autoplay as part of the deferred Music-bed resume window, so a stale non-playing Music callback no longer cancels narration into a retry loop."
        ),
        AppChangelogEntry(
            id: "tvos-foreground-remote-pause-reader-first",
            title: "TV remote pause reaches the reader",
            detail: "Apple TV foreground Siri Remote Play/Pause presses now bypass the broker-echo rejection before force-pause resolution, so a real Living Room pause can stop sentence narration and the Apple Music bed on the first press."
        ),
        AppChangelogEntry(
            id: "direct-player-music-bed-pause-mirror",
            title: "Embedded readers pause together",
            detail: "Direct Apple interactive player embeds now mirror reader-owned Apple Music bed pauses into narration before reinforcing the Music pause, so reusable consumers without the Job/Library shell avoid split Music-only pauses."
        ),
        AppChangelogEntry(
            id: "apple-create-custom-provider-detail-labels",
            title: "Create provider labels stay custom",
            detail: "Apple Create discovery detail rows now prefer the backend-advertised provider option label before falling back to built-in labels, matching Web for custom book/video source providers."
        ),
        AppChangelogEntry(
            id: "create-discovery-friendly-candidate-labels",
            title: "Discovery candidates read cleaner",
            detail: "Web Video Dubbing and Apple Create video/book discovery candidate details now use friendly provider labels instead of raw provider ids, matching the source pickers while preserving token-safe provenance metadata."
        ),
        AppChangelogEntry(
            id: "web-narrate-discovery-friendly-provider-labels",
            title: "Discovery labels stay friendly",
            detail: "Web Narrate Ebook discovery now labels checked providers and candidate source metadata with the same friendly provider names as its source buttons, keeping backend-owned discovery labels consistent with Apple Create."
        ),
        AppChangelogEntry(
            id: "apple-tv-music-bed-toggle-requires-idle-reader",
            title: "TV pause keeps narration first",
            detail: "Apple TV Play/Pause toggles no longer turn into a Music-bed resume while sentence narration is still requested or audible, tightening the single-press pause path across Job and Library playback."
        ),
        AppChangelogEntry(
            id: "download-station-client-hint-dedupe",
            title: "Create handoff hints stay singular",
            detail: "Web Video Dubbing and Apple YouTube Dub now de-duplicate safe Download Station completed-file hints while preserving first-seen order, matching the backend completion metadata contract."
        ),
        AppChangelogEntry(
            id: "download-station-route-metadata-dedupe",
            title: "Downloader metadata avoids repeats",
            detail: "Acquisition job polling now de-duplicates legacy Download Station completed-file metadata after sanitization, so older jobs and mocked poll results present the same single finished artifact list as live backend polling."
        ),
        AppChangelogEntry(
            id: "download-station-completed-file-dedupe",
            title: "Downloader completions stay singular",
            detail: "Download Station polling now collapses repeated completed-file aliases after safe manual-download root normalization, keeping Web and Apple video source handoff from showing the same finished artifact more than once."
        ),
        AppChangelogEntry(
            id: "apple-music-bed-adoption-reader-first",
            title: "Music-bed pause reaches narration first",
            detail: "When tvOS delivers the first Play/Pause edge to Apple Music, the reader now latches the shared pause and notifies Job or Library narration before suppressing the Music surface, so one press has a better chance to stop both audio layers together."
        ),
        AppChangelogEntry(
            id: "backend-video-discovery-bounded-insert",
            title: "Video source scans are lighter",
            detail: "Backend NAS/manual video discovery now keeps bounded newest matches with binary insertion instead of sorting after every candidate, reducing picker work for Web Video Dubbing and Apple YouTube Dub on large download folders."
        ),
        AppChangelogEntry(
            id: "backend-source-picker-hidden-symlink-targets",
            title: "Source pickers hide staging links",
            detail: "Backend source discovery now prunes visible symlinks whose resolved targets live under hidden folders or files, keeping Web and Apple Create EPUB, subtitle, and video pickers from surfacing hidden NAS staging artifacts."
        ),
        AppChangelogEntry(
            id: "apple-tv-music-bed-stopped-mirror-pause",
            title: "TV pause mirrors stopped bed",
            detail: "Apple TV Job and Library playback now treat an Apple Music bed stop while sentence narration is still requested as the same reader pause command, so the first Siri Remote Play/Pause press can stop both the bed and sentence track."
        ),
        AppChangelogEntry(
            id: "apple-youtube-template-sparse-provider-state",
            title: "YouTube templates keep source context",
            detail: "Apple YouTube Dub template saves now recover the discovery provider from source, acquisition, or source-kind provenance when older prepared video handoffs lack a top-level provider, preserving token-free source context for Web/Apple apply-save loops."
        ),
        AppChangelogEntry(
            id: "apple-tv-music-bed-stale-activity-pause",
            title: "TV pause catches stale reader activity",
            detail: "Apple TV now adopts an ignored Apple Music non-playing callback as a reader pause when the Music bed was already known to be active, so a stale reader-active flag cannot leave sentence narration running after the first pause press."
        ),
        AppChangelogEntry(
            id: "apple-music-bed-reader-active-bridge",
            title: "Music-bed pause sees reader intent",
            detail: "Apple Job and Library playback now refresh the Music-bed reader-active bridge from the requested-play state before Music surface changes and reader transport commands, so a single pause can combine Apple Music bed and sentence audio even during autoplay or track handoff timing gaps."
        ),
        AppChangelogEntry(
            id: "apple-tv-music-bed-combined-pause-priority",
            title: "TV pause combines bed and narration",
            detail: "Apple TV now gives explicit Music-bed pause evidence priority over the post-resume stale-event filter, so a single Play/Pause press can stop both Apple Music bed audio and the current sentence track."
        ),
        AppChangelogEntry(
            id: "create-completed-file-client-filtering",
            title: "Create filters completion hints",
            detail: "Web Video Dubbing and Apple YouTube Dub now ignore URL-like, file-scheme, magnet, and traversal values in legacy Download Station completion metadata before displaying or matching refreshed manual-download candidates."
        ),
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
