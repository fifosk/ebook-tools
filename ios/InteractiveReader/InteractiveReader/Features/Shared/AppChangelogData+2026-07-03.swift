extension AppChangelogData {
    static let july3Entries: [AppChangelogEntry] = [
        AppChangelogEntry(
            id: "tvos-active-bed-nonplaying-defers",
            title: "TV bed dips keep reading",
            detail: "Apple TV Music-bed handling now defers ignored non-playing callbacks while narration is active, recovering the bed instead of adopting those MusicKit interruptions as reader pauses that stop book playback."
        ),
        AppChangelogEntry(
            id: "tvos-nonmanual-music-bed-stop-keeps-reader",
            title: "TV bed hiccups keep reading",
            detail: "Apple TV Job and Library playback no longer treat non-manual Apple Music bed non-playing state as a sentence pause while narration is active, so transient MusicKit bed interruptions recover the bed instead of stopping book playback."
        ),
        AppChangelogEntry(
            id: "public-epub-destination-helper",
            title: "Catalog EPUB handoff is tidier",
            detail: "Public-catalog EPUB acquisition now keeps collision-safe destination reservation with the shared EPUB artifact helpers, so Gutenberg and Internet Archive handoffs use the same tested filename/path rules before Create loads them."
        ),
        AppChangelogEntry(
            id: "backend-bounded-source-picker-helper",
            title: "Source pickers share ordering",
            detail: "Backend EPUB, output-folder, manual-download, and acquisition candidate pickers now share one bounded newest-first insertion helper, reducing ordering drift while keeping large NAS source scans lightweight."
        ),
        AppChangelogEntry(
            id: "tvos-startup-music-pause-active-guard",
            title: "TV startup keeps playback alive",
            detail: "Apple TV reader playback now ignores non-manual Apple Music pause observations whenever sentence audio is requested but the AVPlayer is not playing yet, preventing startup Music-bed state from stopping the first sentence."
        ),
        AppChangelogEntry(
            id: "apple-create-discovery-provider-order",
            title: "Apple Create follows source order",
            detail: "Apple Narrate EPUB and YouTube Dub discovery pickers now preserve the backend acquisition-provider response order after provider inventory loads, matching Web and the shared provider catalog while keeping built-in fallback order for offline/no-inventory states."
        ),
        AppChangelogEntry(
            id: "tvos-preaudible-music-pause-guard",
            title: "TV resume waits for narration",
            detail: "Apple TV reader playback now ignores non-manual Apple Music pause observations while sentence audio is requested but not yet audible, even after a prior pause action, preventing the bed state from stopping a resume before narration starts."
        ),
        AppChangelogEntry(
            id: "tvos-startup-music-pause-ignored",
            title: "TV startup ignores Music pause",
            detail: "Apple TV reader playback now ignores Apple Music pause observations while narration is requested but not yet audible, keeping the initial sentence start alive instead of treating the bed state as a reader pause."
        ),
        AppChangelogEntry(
            id: "playback-log-build-stamp-fallback",
            title: "Device logs keep git stamps",
            detail: "Apple playback transport logs now fall back to bundled branch and commit stamp files when Info.plist build metadata is unavailable at runtime, making physical TV captures easier to match to the installed checkpoint."
        ),
        AppChangelogEntry(
            id: "tvos-requested-playback-recovers-before-pause",
            title: "TV startup keeps narration alive",
            detail: "Apple TV Play/Pause events that arrive while sentence playback is requested but not yet audible now recover the reader instead of pausing it because the Apple Music bed is already playing."
        ),
        AppChangelogEntry(
            id: "music-bed-nonplaying-keeps-reader",
            title: "Music bed no longer cuts narration",
            detail: "Apple TV and iPad playback now treat active Apple Music bed non-playing observations as a bed recovery problem instead of a reader pause, preventing spontaneous MusicKit state changes from cutting off sentence audio."
        ),
        AppChangelogEntry(
            id: "music-bed-ignores-sequence-dwell",
            title: "Music bed respects handoffs",
            detail: "Apple Job and Library playback now ignore Apple Music bed play observations while the reader is intentionally dwelling or switching Original/Translation tracks, preventing Music from restarting the outgoing sentence before Translation begins."
        ),
        AppChangelogEntry(
            id: "sequence-cross-track-early-hard-stop",
            title: "Track handoffs stop earlier",
            detail: "Apple Original/Translation sequence handoffs now apply the AVPlayer hard-stop guard at the early handoff boundary for cross-track switches, so a late boundary callback cannot leak a cut-short next sentence before Translation starts."
        ),
        AppChangelogEntry(
            id: "web-discovery-preserves-provider-order",
            title: "Web discovery follows backend order",
            detail: "Web Narrate Ebook and Video Dubbing discovery pickers now preserve the loaded backend acquisition-provider response order instead of applying separate client-side ranks, keeping Web source lists aligned with Apple and the backend catalog."
        ),
        AppChangelogEntry(
            id: "acquisition-provider-catalog-order",
            title: "Discovery sources keep order",
            detail: "Backend acquisition provider ordering now lives in the shared provider catalog and the registry emits providers in that canonical order, keeping Web and Apple Create source pickers aligned as source providers grow."
        ),
        AppChangelogEntry(
            id: "sequence-cross-track-dwell-detaches-old-item",
            title: "Track handoffs drop buffered tails",
            detail: "Apple Original/Translation dwell handoffs now detach the muted outgoing AVPlayer item when the next playable segment switches tracks, cutting off buffered next-sentence tails before Translation starts without clearing reader playback intent."
        ),
        AppChangelogEntry(
            id: "reader-transport-shared-probe-timings",
            title: "TV pause probes stay aligned",
            detail: "Apple Job and Library Music-bed transport now share pause confirmation, playback recovery, and deferred Music resume probe timings through the reader transport resolver, reducing surface drift while tuning TV pause/resume behavior."
        ),
        AppChangelogEntry(
            id: "sequence-track-switch-keeps-hard-stop",
            title: "Track switches hold the stop",
            detail: "Apple Original/Translation track switches now keep the outgoing segment's AVPlayer hard-stop guard latched until the old audio item is replaced, reducing next-sentence audio slivers before Translation starts without clipping same-track seeks."
        ),
        AppChangelogEntry(
            id: "playback-log-current-commit-shortcuts",
            title: "Device log checks pin the build",
            detail: "Apple device playback-log pull-and-verify now has current-commit shortcuts for pause, pause/resume, resume-offset, and combined reader repro captures, so physical tests reject stale installs without manually passing a SHA."
        ),
        AppChangelogEntry(
            id: "playback-log-audio-state-autoplay-reject",
            title: "TV retry loops fail fast",
            detail: "Apple playback transport log verification now fails immediately if Job or Library audio-state callbacks recover pending interactive autoplay, catching stale TV builds that loop a paused sentence before broader retry-loop heuristics."
        ),
        AppChangelogEntry(
            id: "sequence-hard-segment-end-guard",
            title: "Reader handoffs stop at segment end",
            detail: "Interactive reader sequence playback now gives AVPlayer a hard per-segment end time and uses smaller TV boundary/fade windows, reducing clipped sentence endings while blocking a next-sentence sliver before the Original/Translation switch."
        ),
        AppChangelogEntry(
            id: "tvos-autoplay-clear-before-recovery",
            title: "TV playback retries stay paused",
            detail: "Job and Library audio-state callbacks now clear pending autoplay before Music-bed recovery runs, and tvOS track switches use a wider boundary/fade guard so the next sentence is less likely to leak before Translation starts."
        ),
        AppChangelogEntry(
            id: "exact-signed-url-key-sanitizer-parity",
            title: "Signed URLs scrub evenly",
            detail: "Backend, Web, and Apple creation-template sanitizers now share exact sensitive URL keys such as sig and AWS token fields, so signed discovery handoffs are stripped consistently across surfaces."
        ),
        AppChangelogEntry(
            id: "playback-transport-build-header",
            title: "Device logs show build",
            detail: "DEBUG Apple playback transport logs now include a token-safe release, bundle, branch, and commit header before reader events, making physical TV/iPad repro captures easier to match to the deployed checkpoint."
        ),
        AppChangelogEntry(
            id: "sequence-fade-survives-handoff-seek",
            title: "Track handoffs keep fades latched",
            detail: "Interactive reader sequence handoffs now keep the old segment fade attached while the muted AVPlayer seeks or loads, then rebuild the fade only after the new Original or Translation segment lands, reducing stale next-sentence slivers before track switches."
        ),
        AppChangelogEntry(
            id: "sequence-handoff-pauses-old-item",
            title: "Track handoffs stay quiet",
            detail: "Sequence handoffs now pause the muted previous AVPlayer item while preserving reader playback intent, reducing stale next-sentence tails before Original/Translation switches without stopping the Apple Music bed."
        ),
        AppChangelogEntry(
            id: "reader-autoplay-anchor-trim-hardening",
            title: "Reader pauses and skips settle",
            detail: "Job and Library playback now suppress pending autoplay recovery through reader-owned pause holds, single-track skips drop stale slider anchors after the live timeline settles, and TV handoffs keep sentence tails with a narrower same-track trim."
        ),
        AppChangelogEntry(
            id: "reader-pause-confirmation-clears-autoplay",
            title: "TV pauses stop retry loops",
            detail: "Job and Library playback now clear pending interactive autoplay after confirmed reader pauses, and sequence dwell cancels stale audio-ready callbacks before pinning the muted player so TV pauses and Translation handoffs settle cleanly."
        ),
        AppChangelogEntry(
            id: "backend-youtube-library-helper",
            title: "YouTube NAS picker is leaner",
            detail: "Backend YouTube NAS path normalization, linked-job indexing, and video-row serialization now live in a focused helper, keeping Web Video Dubbing and Apple YouTube Dub source pickers aligned outside the route handler."
        ),
        AppChangelogEntry(
            id: "backend-library-media-response-helper",
            title: "Library media contract is leaner",
            detail: "Backend Library media URL normalization, audio/timing-track shaping, and playback diagnostics now live in a focused helper with direct coverage, keeping Web and Apple playback manifests aligned outside the large Library router."
        ),
        AppChangelogEntry(
            id: "tvos-cross-track-handoff-and-pause-latch",
            title: "TV pauses and handoffs latch",
            detail: "Apple TV interactive reader pauses now reinforce the reader-owned Apple Music bed pause immediately, and Original-to-Translation sequence handoffs use wider cross-track boundary/fade headroom so the next sentence is not heard before the track switch."
        ),
        AppChangelogEntry(
            id: "ipad-e2e-space-resume-uses-broker",
            title: "iPad bubble resume test matches keys",
            detail: "The iPad Music-bed debug chrome now routes its E2E Space command through the shared keyboard broker before falling back to a notification, matching the real hardware-key path after lookup-bubble pronunciation pauses."
        ),
        AppChangelogEntry(
            id: "tvos-sequence-balanced-handoff-boundary",
            title: "TV handoffs balance tails",
            detail: "Apple TV sequence handoffs now move the boundary, fade, and muted dwell pin slightly earlier than the previous release without restoring the old extra-wide trim, reducing short next-sentence bleed before Translation starts while preserving sentence tails."
        ),
        AppChangelogEntry(
            id: "tvos-sequence-handoff-preserves-tail",
            title: "TV handoffs keep sentence tails",
            detail: "Apple TV sequence handoffs now back off the extra-wide trim that could clip sentence endings, while stale pending autoplay recovery is cleared when the reader is already paused instead of restarting a loop."
        ),
        AppChangelogEntry(
            id: "apple-single-track-stream-isolation",
            title: "Single-track playback stays isolated",
            detail: "Original-only and Translation-only reader modes now narrow combined audio options to the requested stream URL before loading, while tvOS sequence handoffs keep a larger output-buffer guard so the next original sentence cannot leak before Translation starts."
        ),
        AppChangelogEntry(
            id: "sequence-eof-owned-by-controller",
            title: "Sequence EOF avoids chunk jumps",
            detail: "Interactive reader sequence playback now treats AVPlayer item-end notifications as segment fallbacks only while the sequence controller is active, ignoring late EOF during dwell or track transitions so playback does not jump chunks, loop, or leak a next-sentence sliver before Translation starts."
        ),
        AppChangelogEntry(
            id: "tvos-sequence-extra-safe-handoff-boundary",
            title: "TV handoffs trim earlier",
            detail: "Apple TV sequence handoffs now use an extra-conservative same-track trim, earlier boundary, and longer decode fade only on tvOS, reducing the audible next-original-sentence sliver before Translation starts."
        ),
        AppChangelogEntry(
            id: "reader-pause-clears-autoplay-token",
            title: "Reader pauses stop stale retries",
            detail: "Apple Job and Library reader-owned pauses now hard-cancel pending interactive autoplay before stopping narration, so stale retry tokens cannot restart or loop playback while the Apple Music bed pause is settling."
        ),
        AppChangelogEntry(
            id: "tvos-sequence-wider-preroll-trim",
            title: "TV handoffs trim more preroll",
            detail: "Apple TV sequence playback now trims a wider same-track preroll window before Original-to-Translation handoff, reducing cut-short next-sentence audio when metadata gates leave a hidden preroll tail."
        ),
        AppChangelogEntry(
            id: "apple-reader-audio-state-autoplay-guard",
            title: "Reader retries avoid loops",
            detail: "Apple Job and Library playback no longer let rapid audio-state callbacks start pending interactive autoplay recovery, leaving recovery to explicit retry and watchdog paths while Music-bed pauses settle."
        ),
        AppChangelogEntry(
            id: "sequence-handoff-clears-stale-audio",
            title: "Track switches stay silent",
            detail: "Interactive reader sequence track switches now silence playback, clear stale fades, and remove stale boundary observers before loading the next Original or Translation item, reducing out-of-order audio tails during handoff."
        ),
        AppChangelogEntry(
            id: "tvos-sequence-handoff-wider-guard",
            title: "TV handoffs avoid audio slivers",
            detail: "Apple TV sequence playback now restores a wider fade and same-track trim safety margin, and ignores persistent-stall recovery during intentional handoff dwell so the next sentence cannot leak before the Translation track switch."
        ),
        AppChangelogEntry(
            id: "tvos-autoplay-recovery-attempt-cap",
            title: "TV autoplay retries settle",
            detail: "Apple TV Job and Library playback now cap pending interactive autoplay recovery retries for the same sentence, so a stuck resume cannot keep re-jumping the reader while the Apple Music bed pause is settling."
        ),
        AppChangelogEntry(
            id: "backend-download-station-status-helper",
            title: "Downloader polling is leaner",
            detail: "Backend Download Station status parsing, completed-file normalization, task messages, and value coercion now live in a focused acquisition helper, keeping downloader polling behavior shared by Web and Apple Create easier to test."
        ),
        AppChangelogEntry(
            id: "tvos-pause-hold-clears-autoplay",
            title: "TV pause holds stop retries",
            detail: "Apple TV Job and Library playback now clear pending interactive autoplay when the reader is stopped inside the pause-hold window, preventing late MusicKit state from restarting the same sentence after a pause."
        ),
        AppChangelogEntry(
            id: "tvos-sequence-earlier-boundary",
            title: "TV handoffs switch cleaner",
            detail: "Apple TV sequence handoffs now trigger earlier while keeping the fade ramp start stable, reducing the short next-sentence leak before the Translation track switch without widening the audible fade tail."
        ),
        AppChangelogEntry(
            id: "tvos-paused-autoplay-recovery-hard-stop",
            title: "TV pause blocks stale retries",
            detail: "Apple TV Job and Library playback now refuse pending interactive autoplay recovery while reader transport is in any paused Music-bed state, preventing stale retry loops after a pause command."
        ),
        AppChangelogEntry(
            id: "sequence-tight-preroll-trim",
            title: "Track handoffs trim preroll",
            detail: "Interactive reader sequence playback now trims very tight same-track sentence gates before handoff, so a tiny preroll from the next sentence is not heard before the Translation track starts."
        ),
        AppChangelogEntry(
            id: "sequence-dwell-pin-at-handoff-boundary",
            title: "Reader handoffs avoid late pins",
            detail: "Interactive reader sequence dwell now pins the muted AVPlayer at or before the early handoff boundary instead of seeking closer to the nominal sentence end, reducing TV and iPad cases where a sliver of the next sentence leaks before the Translation track starts."
        ),
        AppChangelogEntry(
            id: "acquisition-readable-source-paths",
            title: "Discovery paths stay readable",
            detail: "Backend acquisition providers now keep source labels for unavailable local EPUB and NAS video roots while only publishing source paths for roots that are currently readable, so Web and Apple Create avoid stale picker paths during NAS outages."
        ),
        AppChangelogEntry(
            id: "tvos-sequence-fade-ends-at-handoff",
            title: "TV handoff fades end earlier",
            detail: "Interactive reader sequence playback now fades the active audio track to silence at the same early handoff boundary used by the TV boundary observer, preventing a short piece of the next sentence from leaking before the translation track starts."
        ),
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
            id: "sequence-gates-trim-overlaps",
            title: "Sequence gates avoid overlaps",
            detail: "Web and Apple sequence playback now trim overlapping or tightly adjacent same-track sentence gates just before the next sentence start while keeping wider gaps intact, so loose original or translation end gates cannot leak a buffered sliver of the following sentence before the handoff."
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
