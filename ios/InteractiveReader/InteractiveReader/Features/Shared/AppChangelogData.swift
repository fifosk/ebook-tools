enum AppChangelogData {
    static let days: [AppChangelogDay] = [
        AppChangelogDay(
            id: "2026-07-01",
            dateLabel: "July 1, 2026",
            version: "2026.07.01.001",
            entries: [
                AppChangelogEntry(
                    id: "youtube-video-download-safe-exists",
                    title: "YouTube downloads tolerate NAS races",
                    detail: "YouTube video download recovery now checks completed partials and prepared yt-dlp fallback files through NAS-tolerant stat probes, reducing transient source import failures shared by Web and Apple video Create flows."
                ),
                AppChangelogEntry(
                    id: "public-epub-acquire-safe-verify",
                    title: "Public EPUB imports verify safely",
                    detail: "Reviewed Gutenberg and Internet Archive EPUB acquisition now verifies downloaded files through the same NAS-tolerant stat helper used by source discovery, returning a controlled error if final metadata cannot be read."
                ),
                AppChangelogEntry(
                    id: "video-discovery-bounded-newest",
                    title: "Video source pickers stay lighter",
                    detail: "Backend NAS and manual-download video discovery now keeps only the newest requested candidates while scanning, so Web and Apple Create source pickers avoid building giant intermediate lists from large download folders."
                ),
                AppChangelogEntry(
                    id: "tvos-ignored-music-pause-active-reader",
                    title: "TV first pause reaches narration",
                    detail: "Apple TV Music-bed playback now converts an otherwise ignored Music non-playing signal into a reader-owned pause while sentence narration is active, so a Siri Remote pause routed to Music should not leave the track playing until a second press."
                ),
                AppChangelogEntry(
                    id: "youtube-dub-generation-safe-stats",
                    title: "YouTube dubbing probes are NAS-tolerant",
                    detail: "Backend YouTube dubbing submission, generation, artifact handling, and video helper output paths now validate selected media, recovered partial downloads, and temporary mux artifacts through tolerant stat helpers, reducing flaky NAS path failures shared by Web and Apple Create flows."
                ),
                AppChangelogEntry(
                    id: "tvos-active-music-pause-confirms-reader",
                    title: "TV Music pauses confirm reader pause",
                    detail: "Apple TV now confirms a Music-bed non-playing signal during active narration before treating it as a reader-owned pause, so a Siri Remote pause routed to Apple Music should stop the sentence track without waiting for a second press."
                ),
                AppChangelogEntry(
                    id: "tvos-watchdog-stray-music-play-latch",
                    title: "TV pause latch watches Music",
                    detail: "Apple TV reader playback now lets the Music-bed watchdog reassert a reader-owned pause when Apple Music starts playing again without an explicit reader resume, targeting Cinema logs with repeated broker pauses and no intervening play."
                ),
                AppChangelogEntry(
                    id: "tvos-interactive-start-music-bed-gate",
                    title: "TV interactive starts gate Music",
                    detail: "Apple TV interactive playback now routes jump/resume-style starts through the same deferred Apple Music bed resume used by reader Play/Pause, and the tvOS Music-bed simulator journey proves that path before remote pause testing."
                ),
                AppChangelogEntry(
                    id: "tvos-command-center-idempotent-bed-controls",
                    title: "TV bed controls ignore stale echoes",
                    detail: "Apple TV reader Now Playing play/pause callbacks now stay idempotent while the physical Play/Pause path remains a toggle, reducing Music-bed echo races where a stale command could pause only one playback layer."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-30",
            dateLabel: "June 30, 2026",
            version: "2026.06.30.001",
            entries: [
                AppChangelogEntry(
                    id: "tvos-cinema-stray-music-play-latch",
                    title: "Cinema pauses stay latched",
                    detail: "Apple TV reader playback now reasserts a reader-owned pause if Apple Music reports a stray play before an explicit reader resume, and the device log verifier catches repeated broker pauses without an intervening reader play."
                ),
                AppChangelogEntry(
                    id: "web-reading-bed-admin-route-contract",
                    title: "Reading bed admin routes share helpers",
                    detail: "Web reading-bed upload, rename, and delete actions now use a shared route contract with encoded bed IDs, keeping the admin panel aligned with the playback reading-bed catalog routes."
                ),
                AppChangelogEntry(
                    id: "reading-bed-file-runtime-contract",
                    title: "Reading bed files share contracts",
                    detail: "Backend runtime metadata now advertises the reading-bed file route and Apple playback builds online bed URLs through the shared playback-state template instead of a hardcoded path."
                ),
                AppChangelogEntry(
                    id: "reading-bed-runtime-contract",
                    title: "Reading beds share playback contracts",
                    detail: "The Web reading-bed catalog client now uses the same playback-state runtime contract that Apple Settings and Apple playback validate, reducing another hardcoded cross-surface route."
                ),
                AppChangelogEntry(
                    id: "tvos-adopted-music-pause-echo-guard",
                    title: "TV adopted pauses resist remote echoes",
                    detail: "Apple TV now gives Music-adopted reader pauses a longer broker-echo guard and emits earlier fullscreen-suppression proof, covering Cinema logs where a delayed Play/Pause callback resumed narration just after the ordinary guard."
                ),
                AppChangelogEntry(
                    id: "sentence-image-runtime-contract",
                    title: "Sentence image routes share contracts",
                    detail: "Backend runtime metadata now advertises sentence-image info, batch lookup, and regeneration endpoints, with Web clients using those templates and Apple Settings validating the same media contract."
                ),
                AppChangelogEntry(
                    id: "web-offline-export-runtime-contract",
                    title: "Web exports share runtime contracts",
                    detail: "Web offline export downloads now use the same backend-advertised export download template, source kinds, and player type contract that Apple Settings and device readiness validate."
                ),
                AppChangelogEntry(
                    id: "tvos-active-music-pause-defers-first",
                    title: "TV active Music blips recover first",
                    detail: "Apple TV Music-bed playback now routes non-playing MusicKit observations during active sentence narration through the recovery/defer path before any reader-pause adoption, reducing accidental Cinema pauses while keeping explicit remote pauses latched."
                ),
                AppChangelogEntry(
                    id: "library-actions-runtime-contract-parity",
                    title: "Library routes share runtime contracts",
                    detail: "The backend runtime descriptor now advertises Library access, media removal, metadata refresh, enrichment, reindex, and source routes together, with Web clients and Apple Settings validating the same contract before device testing."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-dead-resume-recovery",
                    title: "TV resume restores silent readers",
                    detail: "Apple TV and iPad reader Play/Pause now recreates the current sentence autoplay request before resuming a paused Music bed, and recovery retries rebuild the narration request instead of accepting a Music-only dead resume."
                ),
                AppChangelogEntry(
                    id: "pipeline-job-runtime-contract-parity",
                    title: "Pipeline job routes share runtime contracts",
                    detail: "Web and Apple now advertise the same pipeline job action, access, metadata, book lookup, cover upload, and cover-serving endpoints through the public runtime descriptor instead of relying on Web-only hardcoded paths."
                ),
                AppChangelogEntry(
                    id: "tvos-passive-music-pause-deferred",
                    title: "TV passive Music stops recover first",
                    detail: "Apple TV no longer immediately converts a passive Apple Music non-playing observation during active narration into a reader pause; it now tries the existing bed recovery path first and only adopts a persistent stop."
                ),
                AppChangelogEntry(
                    id: "subtitle-youtube-runtime-route-parity",
                    title: "Subtitle routes share runtime contracts",
                    detail: "Web subtitle and YouTube helper calls now use the same backend runtime descriptor paths that Apple Settings validates, including job metadata lookup, subtitle result, YouTube download, and NAS delete endpoints."
                ),
                AppChangelogEntry(
                    id: "tvos-reader-resume-restores-narration",
                    title: "TV resume restores narration",
                    detail: "Apple TV and iPad reader resume now rebuild the current sentence playback request before restarting the Apple Music bed when a paused transport lost its narration request, reducing Music-only resumes after lookup or remote Play/Pause."
                ),
                AppChangelogEntry(
                    id: "create-epub-picker-bounded-limit",
                    title: "Large EPUB pickers can stay lighter",
                    detail: "The shared backend EPUB picker now supports an optional newest-first limit with token-safe telemetry, giving Web and Apple Create a tested low-payload path for very large NAS book roots while preserving the default full listing."
                ),
                AppChangelogEntry(
                    id: "tvos-active-music-pause-immediate",
                    title: "TV first pause adopts immediately",
                    detail: "Apple TV now treats an Apple Music non-playing signal during active sentence playback as the reader transport pause before trying bed recovery, so the first Siri Remote pause should stop narration and Music together."
                ),
                AppChangelogEntry(
                    id: "tvos-stale-pause-no-longer-masks-real-pause",
                    title: "TV pauses no longer split Music and narration",
                    detail: "Apple TV no longer lets the post-adoption reader-paused flag classify a real Siri Remote pause after resume as a stale MusicKit echo, so one pause should stop both the Apple Music bed and sentence narration."
                ),
                AppChangelogEntry(
                    id: "tvos-music-pause-adoption-replay",
                    title: "TV first pause latches narration",
                    detail: "Apple TV now replays a missed Music-bed pause adoption to the active reader and latches the reader pause even during sentence-boundary gaps, so one Siri Remote pause should not stop only Apple Music before a second press stops narration."
                ),
                AppChangelogEntry(
                    id: "tvos-music-persistent-pause-converges",
                    title: "TV pause converges both tracks",
                    detail: "Apple TV Music-bed playback now gives transient MusicKit non-playing updates one recovery attempt, then treats a still-stopped bed as a reader pause so a Siri Remote pause cannot leave music stopped while sentence narration keeps playing."
                ),
                AppChangelogEntry(
                    id: "tvos-passive-music-pause-recovers-reader",
                    title: "TV lookup resume resists Music wobbles",
                    detail: "Apple TV now treats transient Apple Music non-playing updates during active narration as recoverable bed-state changes before adopting them as reader pauses, so lookup-bubble resume is not stopped by a passive Music playback refresh."
                ),
                AppChangelogEntry(
                    id: "apple-web-create-handoff-source",
                    title: "Web Create handoff is clearer",
                    detail: "Apple Create now marks Open Web Create links as Apple-origin handoffs, and Web Create preserves that token-free source when saving generated-book, Narrate EPUB, subtitle, or YouTube dubbing templates."
                ),
                AppChangelogEntry(
                    id: "living-room-candidate-gate",
                    title: "Living Room checks are one command",
                    detail: "The Apple pipeline now has a repeatable Living Room TV candidate gate that runs the full non-physical shared pipeline plus the real tvOS Music-bed simulator journey before any requested physical install."
                ),
                AppChangelogEntry(
                    id: "tvos-music-pause-direct-adoption",
                    title: "TV Music pauses stop narration",
                    detail: "Apple TV Library and Job playback now register a direct Music-bed pause adoption handler, so a Siri Remote pause that reaches Apple Music first immediately pauses sentence narration instead of waiting on a later SwiftUI state update."
                ),
                AppChangelogEntry(
                    id: "apple-device-playback-log-pull",
                    title: "Device playback logs are recoverable",
                    detail: "DEBUG Apple builds now persist token-safe playback transport breadcrumbs in the app cache, and the device pipeline can pull that file after a physical repro when CoreDevice live console captures only launch-wrapper output."
                ),
                AppChangelogEntry(
                    id: "apple-device-playback-log-archives",
                    title: "Device playback logs are archived",
                    detail: "The physical-device playback transport pull helper now preserves timestamped app-cache and CoreDevice log archives, so repeated Apple TV repro pulls keep the best pause/resume evidence."
                ),
                AppChangelogEntry(
                    id: "apple-device-playback-log-verifier",
                    title: "Device playback logs are verifiable",
                    detail: "Pulled playback transport logs now have a Makefile verifier for pause-only and pause/resume repros, giving physical Apple TV tests a pass/fail fallback when live Now Playing console breadcrumbs are unavailable."
                ),
                AppChangelogEntry(
                    id: "tvos-adopted-pause-resume-window",
                    title: "TV resume responds sooner",
                    detail: "Apple TV adopted Music-bed pauses now use the same 1.5-second broker echo window as ordinary reader pauses, so deliberate resume presses after that guard are no longer swallowed by a longer Music-specific hold."
                ),
                AppChangelogEntry(
                    id: "tvos-play-pause-explicit-resume-only",
                    title: "TV Play/Pause avoids echo resumes",
                    detail: "Apple TV reader Play/Pause no longer uses the hardware-echo fast resume path after a reader-owned pause; resume now goes through the explicit reader play/toggle transport so delayed remote callbacks cannot restart the Music bed and sentence track accidentally."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-slow-resume-guard",
                    title: "TV Music resume stays reader-owned",
                    detail: "Apple TV Job and Library playback now keep stale Apple Music pause signals from re-pausing narration while a reader-owned Play is still restoring the bed, reducing cases where resume required another remote press."
                ),
                AppChangelogEntry(
                    id: "release-2026-06-30-001",
                    title: "Release marker moves to today",
                    detail: "The visible Apple app release badge and in-app changelog now start a June 30 checkpoint for the latest shared pipeline dogfood work."
                ),
                AppChangelogEntry(
                    id: "tvos-transport-distinct-presses-june30",
                    title: "TV Play/Pause accepts real turns",
                    detail: "Apple TV now treats opposite Play/Pause actions inside the duplicate window as real remote presses while still filtering same-action echoes, reducing cases where only the Apple Music bed paused before narration."
                ),
                AppChangelogEntry(
                    id: "tvos-foreground-pause-echo-guard",
                    title: "TV foreground pause stays paused",
                    detail: "Apple TV foreground Play/Pause handling now uses the same reader-pause echo guard as the app-wide broker, so a Music-surface pause cannot bounce back into an accidental reader resume before the explicit next press."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-resume-bed-sequencing",
                    title: "TV lookup resume is calmer",
                    detail: "Apple TV reader resume from lookup now waits for narration to become active before restarting the Apple Music bed, cancels delayed bed resume work when a fresh lookup or Music-surface reader pause lands, ignores stale MusicKit pause mirrors after an accepted resume, and sequence dwell pins muted playback at sentence boundaries to reduce next-sentence audio bleed."
                ),
                AppChangelogEntry(
                    id: "tvos-stale-music-pause-deferred-bed-resume",
                    title: "TV resume waits for narration",
                    detail: "Job and Library playback now route stale MusicKit pause adoption after an accepted reader Play through the same deferred bed-resume gate, so Apple Music cannot restart ahead of sentence narration."
                ),
                AppChangelogEntry(
                    id: "tvos-paused-bed-mirror-idempotent",
                    title: "TV remote pauses stay latched",
                    detail: "Apple TV reader screens now register with the app-wide Play/Pause broker while interactive book playback is active, and Music-bed pause mirroring is idempotent once narration is already paused so later MusicKit surface updates do not re-run the reader-pause handoff."
                ),
                AppChangelogEntry(
                    id: "acquisition-url-credentials-stripped",
                    title: "Discovery links hide credentials",
                    detail: "Discovery and downloader handoffs now strip URL user-info credentials from public acquisition metadata and reject credential-bearing signed handoff URLs before Web or Apple Create can reuse them."
                ),
                AppChangelogEntry(
                    id: "acquisition-fragment-credentials-stripped",
                    title: "Discovery fragments hide tokens",
                    detail: "Acquisition metadata now strips sensitive key/value URL fragments, and signed discovery handoff tokens reject fragment credentials before downloader reuse."
                ),
                AppChangelogEntry(
                    id: "acquisition-url-safety-shared",
                    title: "Discovery scrubbing is shared",
                    detail: "Acquisition token signing and public route serialization now share one URL-safety helper so Web and Apple discovery handoffs use the same credential-scrubbing rules."
                ),
                AppChangelogEntry(
                    id: "creation-template-url-safety-shared",
                    title: "Saved templates scrub discovery links",
                    detail: "Saved Create templates now reuse the shared URL-safety helper so discovery-state URLs cannot persist user-info credentials, private tracker query keys, or token fragments before Web or Apple reuse."
                ),
                AppChangelogEntry(
                    id: "client-template-url-safety",
                    title: "Create drafts scrub links earlier",
                    detail: "Web and Apple Create now scrub discovery-state URL credentials before saving templates, keeping client-side book and video template drafts aligned with the backend guard."
                ),
                AppChangelogEntry(
                    id: "apple-metadata-template-safety",
                    title: "Metadata templates scrub earlier",
                    detail: "Apple Create now scrubs subtitle and YouTube metadata drafts with the same recursive template-safety rules before applying or saving templates."
                ),
                AppChangelogEntry(
                    id: "offline-export-metadata-safety",
                    title: "Offline exports scrub metadata",
                    detail: "Offline export manifests now recursively remove sensitive metadata keys and scrub credential-bearing URLs before Apple and Web offline players receive them."
                ),
                AppChangelogEntry(
                    id: "offline-export-gate-covers-manifest",
                    title: "Offline export gate is stronger",
                    detail: "The backend offline-export checkpoint now runs the manifest metadata scrubber test alongside export route tests, so reusable Apple pipeline validation covers both route and archive payload safety."
                ),
                AppChangelogEntry(
                    id: "url-safety-contract-parity",
                    title: "URL safety stays aligned",
                    detail: "Apple contract tests now compare backend, Web, and Apple URL-safety markers plus public URL schemes directly, preventing template and offline-export scrubbing rules from drifting across surfaces."
                ),
                AppChangelogEntry(
                    id: "notification-route-template-parity",
                    title: "Notification routes match runtime",
                    detail: "Notification device-removal routing now uses the same device-id path template advertised by system runtime metadata, and backend tests compare that descriptor with FastAPI routes."
                ),
                AppChangelogEntry(
                    id: "runtime-api-route-table-parity",
                    title: "Runtime paths match routes",
                    detail: "Runtime descriptor tests now compare every advertised API path and path template against FastAPI routes, aligning library media file streaming on the shared file-path template."
                ),
                AppChangelogEntry(
                    id: "runtime-descriptor-focused-gate",
                    title: "Runtime drift fails earlier",
                    detail: "The focused backend runtime descriptor gate now runs the full route-table parity check, so shared Apple preflight catches descriptor drift without the full Web API suite."
                ),
                AppChangelogEntry(
                    id: "runtime-descriptor-changed-tests",
                    title: "Runtime checks are selected",
                    detail: "Changed-test selection now routes runtime descriptor source and contract edits through the focused backend runtime descriptor gate automatically."
                ),
                AppChangelogEntry(
                    id: "readiness-hook-changed-tests",
                    title: "Readiness hooks pick gates",
                    detail: "Changed-test selection now routes Apple deploy and Create readiness hook edits through both runtime descriptor and Apple contract gates."
                ),
                AppChangelogEntry(
                    id: "shared-manifest-full-checkpoint",
                    title: "Pipeline manifest keeps slices",
                    detail: "The shared Apple pipeline manifest validator now requires the full repo-owned backend and Web checkpoint target lists, preventing focused safety slices from being dropped."
                ),
                AppChangelogEntry(
                    id: "shared-manifest-known-targets",
                    title: "Pipeline targets must exist",
                    detail: "Shared Apple pipeline manifest validation now rejects make commands that point at targets absent from this repo's Makefile, catching manifest typos before orchestration dry-runs."
                ),
                AppChangelogEntry(
                    id: "shared-manifest-journey-targets",
                    title: "Journey targets must exist",
                    detail: "Shared Apple pipeline manifest validation now requires UI-test and macOS iPad-style app-owned journeys and verifies each journey's Makefile target exists before orchestration dry-runs."
                ),
                AppChangelogEntry(
                    id: "shared-manifest-aggregate-journeys",
                    title: "Journey dry-runs stay aligned",
                    detail: "Shared Apple pipeline manifest validation now checks APPLE_PIPELINE_JOURNEY_PROFILES against registered app-owned journeys, keeping aggregate dry-runs aligned with local lanes."
                ),
                AppChangelogEntry(
                    id: "create-template-readonly-summary",
                    title: "Templates show details",
                    detail: "Apple Create saved-template pickers now show compact read-only details for the selected template, including type, last update, saved-field count, and token-safe discovery provider/source kind."
                ),
                AppChangelogEntry(
                    id: "create-template-detail-readiness",
                    title: "Template detail is preflighted",
                    detail: "Apple Create readiness now probes the authenticated single-template route with a synthetic missing id, treating a clean 404 as route-ready before simulator or device runs."
                ),
                AppChangelogEntry(
                    id: "template-detail-lookup-optimized",
                    title: "Template details load lighter",
                    detail: "Creation-template detail lookups now scan raw stored ids and normalize only the matching template payload, avoiding extra work for unrelated saved drafts during Web and Apple handoffs."
                ),
                AppChangelogEntry(
                    id: "template-delete-missing-optimized",
                    title: "Template cleanup is lighter",
                    detail: "Missing creation-template deletes now scan raw stored ids before normalizing payloads, so stale Web and Apple cleanup requests avoid extra work on unrelated saved drafts."
                ),
                AppChangelogEntry(
                    id: "create-template-stale-delete-prunes",
                    title: "Stale templates clean up smoothly",
                    detail: "Apple Create now treats a missing saved-template delete as stale local state, pruning the row and resolving selection instead of leaving a dead template with a generic error."
                ),
                AppChangelogEntry(
                    id: "template-mode-filter-optimized",
                    title: "Template pickers filter lighter",
                    detail: "Filtered creation-template lists now scan raw stored modes before normalizing payloads, so mode-specific Web and Apple template pickers avoid touching unrelated saved drafts."
                ),
                AppChangelogEntry(
                    id: "apple-template-mode-filter-dogfood",
                    title: "Apple template filtering is mode-aware",
                    detail: "Apple Create now requests saved templates with the current canonical job mode and refreshes on mode changes, dogfooding the lighter backend template filter from iPhone, iPad, and TV."
                ),
                AppChangelogEntry(
                    id: "create-readiness-template-mode-probe",
                    title: "Template filtering is preflighted",
                    detail: "Apple Create readiness now probes all canonical mode-filtered saved-template lists, catching regressions in every lighter template picker route before simulator or device deployment."
                ),
                AppChangelogEntry(
                    id: "create-template-mode-contract",
                    title: "Template modes stay aligned",
                    detail: "Apple contract tests now compare backend creation-template modes, Apple Create mode mapping, and readiness mode probes so future template modes cannot drift silently between surfaces."
                ),
                AppChangelogEntry(
                    id: "template-mode-change-selection",
                    title: "Template changes run the right gates",
                    detail: "Changed-test selection now routes creation-template backend schema, service, and route edits through backend template tests plus Apple contracts, so the cross-surface mode guard runs when it matters."
                ),
                AppChangelogEntry(
                    id: "web-template-mode-contract",
                    title: "Web template modes are guarded",
                    detail: "Apple contract tests now include Web's creation-template DTO mode union, and changed-test selection routes shared Web DTO edits through the focused template and Apple contract gates."
                ),
                AppChangelogEntry(
                    id: "web-template-route-contract",
                    title: "Web template routes are guarded",
                    detail: "Runtime descriptor contracts now verify Web's creation-template client path against the canonical backend Create template route, and Web template-client edits run Apple contracts."
                ),
                AppChangelogEntry(
                    id: "web-generated-book-route-contract",
                    title: "Generated-book routes are guarded",
                    detail: "Runtime descriptor contracts now compare Web's generated-book options and jobs paths with the canonical backend Create routes, and Web generated-book API edits run focused Create plus Apple contract gates."
                ),
                AppChangelogEntry(
                    id: "web-acquisition-route-contract",
                    title: "Acquisition routes are guarded",
                    detail: "Runtime descriptor contracts now compare Web's acquisition discovery and download handoff client paths with the canonical backend Create routes, and Web jobs API edits run Apple contracts."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-youtube-route-contract",
                    title: "Subtitle routes are guarded",
                    detail: "Runtime descriptor contracts now compare Web's subtitle and YouTube Create client paths with the canonical backend and Apple routes, and Web subtitle API edits run both focused subtitle/video gates plus Apple contracts."
                ),
                AppChangelogEntry(
                    id: "web-playback-route-contract",
                    title: "Playback routes are guarded",
                    detail: "Runtime descriptor contracts now compare Web media and resume client paths with the canonical Apple playback and export routes, and Web media/resume API edits run focused Web gates plus Apple contracts."
                ),
                AppChangelogEntry(
                    id: "web-library-route-contract",
                    title: "Library routes are guarded",
                    detail: "Runtime descriptor contracts now compare Web Library action and media client paths with the canonical Apple Library routes, and Web Library API edits run focused Library plus Apple contracts."
                ),
                AppChangelogEntry(
                    id: "web-auth-route-contract",
                    title: "Auth routes are guarded",
                    detail: "Runtime descriptor contracts now compare Web auth login, OAuth, and session client paths with the canonical Apple auth routes, and Web auth API edits run focused auth plus Apple contracts."
                ),
                AppChangelogEntry(
                    id: "web-client-parity-selector-guard",
                    title: "Parity gates self-check",
                    detail: "Changed-test selector tests now derive Web clients from the runtime descriptor contract and require Apple contracts for each future Web and Apple parity addition."
                ),
                AppChangelogEntry(
                    id: "runtime-payload-section-guard",
                    title: "Runtime payload checks are broader",
                    detail: "The standalone Apple runtime payload checker now verifies every public descriptor section, including exact array values, so simulator and device preflights catch non-Create contract drift."
                ),
                AppChangelogEntry(
                    id: "runtime-model-field-guard",
                    title: "Runtime models stay aligned",
                    detail: "Apple runtime descriptor model tests now derive every Swift contract field and optionality expectation from backend descriptor constants, catching partial decode-model updates before preflight."
                ),
                AppChangelogEntry(
                    id: "runtime-constant-section-guard",
                    title: "Runtime constants stay aligned",
                    detail: "Apple runtime contract constants now expose auth token transport, pipeline cache-buster, and offline export player-type arrays through Swift constants, with tests comparing every advertised backend descriptor value against Apple clients."
                ),
                AppChangelogEntry(
                    id: "web-runtime-contract-module",
                    title: "Web runtime routes are shared",
                    detail: "Web auth and resume clients now use a shared runtime-contract route module mirrored from the backend runtime descriptor, and changed-test selection treats that module as both Web and Apple contract-sensitive."
                ),
                AppChangelogEntry(
                    id: "web-playback-runtime-routes",
                    title: "Web playback routes are shared",
                    detail: "Web media, live-media, bookmark, bookmark-delete, and offline-export create calls now use the shared runtime-contract route module, extending backend/Web/Apple path parity into playback-focused Web tests."
                ),
                AppChangelogEntry(
                    id: "web-library-runtime-routes",
                    title: "Web Library routes are shared",
                    detail: "Web Library item, move/remove, upload-source, ISBN, enrichment, and Library-media calls now use the shared runtime-contract route module, keeping Web Library routes aligned with backend and Apple clients."
                ),
                AppChangelogEntry(
                    id: "web-create-runtime-routes",
                    title: "Web Create routes are shared",
                    detail: "Web generated-book options/jobs and creation-template list/detail calls now use the shared runtime-contract route module, bringing another Create handoff slice under backend/Web/Apple path parity."
                ),
                AppChangelogEntry(
                    id: "web-acquisition-runtime-routes",
                    title: "Web acquisition routes are shared",
                    detail: "Web acquisition provider, discovery, acquire, prepare, and downloader job calls now share the same runtime-contract routes as Apple Create, with focused Web jobs tests covering encoded artifact and task ids."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-runtime-routes",
                    title: "Web subtitle routes are shared",
                    detail: "Web subtitle source, YouTube dubbing, subtitle job, and assistant lookup calls now use shared runtime-contract route constants, with a direct API-client test covering encoded source and video queries."
                ),
                AppChangelogEntry(
                    id: "web-pipeline-source-runtime-routes",
                    title: "Web source routes are shared",
                    detail: "Web pipeline file, default, intake, content-index, upload, LLM, image-node, and voice inventory helpers now use the shared Create runtime contract, with focused Web API tests covering encoded source paths."
                ),
                AppChangelogEntry(
                    id: "web-media-search-runtime-routes",
                    title: "Web media routes are shared",
                    detail: "Web voice preview synthesis and media search now use shared Linguist and Create runtime-contract routes, with focused media API tests covering encoded search queries."
                ),
                AppChangelogEntry(
                    id: "web-pipeline-job-runtime-routes",
                    title: "Web job routes are shared",
                    detail: "Web pipeline submit, list, status, restart, delete, event, timing, and lookup-cache helpers now use the shared runtime contracts, with focused Web tests covering encoded job and lookup terms."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-metadata-runtime-routes",
                    title: "Web subtitle metadata routes are shared",
                    detail: "Web subtitle model, metadata fetch, and TV/YouTube metadata cache-clear helpers now use shared Create and PipelineMedia runtime-contract routes, with focused Web tests covering encoded subtitle job ids."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-29",
            dateLabel: "June 29, 2026",
            version: "2026.06.29.031",
            entries: [
                AppChangelogEntry(
                    id: "tvos-transport-distinct-presses",
                    title: "TV Play/Pause accepts real turns",
                    detail: "Apple TV now treats opposite Play/Pause actions inside the duplicate window as real remote presses while still filtering same-action echoes, reducing cases where only the Apple Music bed paused before narration."
                ),
                AppChangelogEntry(
                    id: "ipad-lookup-space-resumes-reader-bed",
                    title: "iPad space resumes lookup pauses",
                    detail: "iPad spacebar playback now resumes both sentence audio and the Apple Music bed after a lookup bubble pause, even if the pronunciation path briefly changes reader state."
                ),
                AppChangelogEntry(
                    id: "tvos-active-duplicate-pause-accepted",
                    title: "TV pause reaches active narration",
                    detail: "Apple TV now accepts a repeated pause command while reader audio is still active, so a Music-bed pause echo cannot leave sentence narration playing."
                ),
                AppChangelogEntry(
                    id: "tvos-music-ignored-pause-adoption",
                    title: "TV first pause cannot be swallowed",
                    detail: "Apple TV now converts an ignored Apple Music non-playing event into a reader-owned pause when narration is active, preventing the first remote Play/Pause press from pausing only the bed music."
                ),
                AppChangelogEntry(
                    id: "public-catalog-prepare-keeps-provenance",
                    title: "Catalog handoffs keep provenance",
                    detail: "Reviewed Gutenberg and Internet Archive acquisition artifacts now carry token-safe public catalog ids and source URLs into prepare, keeping Web and Apple Create templates stable after acquire-then-prepare handoffs."
                ),
                AppChangelogEntry(
                    id: "download-station-completed-files-safe-roots",
                    title: "Downloader completions are safer",
                    detail: "Download Station polling now returns completed-file hints only when they resolve under configured manual/download roots, dropping URL-like or outside-root entries before Web and Apple Create reconnect to local artifacts."
                ),
                AppChangelogEntry(
                    id: "creation-template-storage-safe-stat",
                    title: "Create templates tolerate storage hiccups",
                    detail: "Saved creation-template reads now use the backend's tolerant storage probe, keeping Web and Apple Create template lists stable when shared storage briefly disappears."
                ),
                AppChangelogEntry(
                    id: "tvos-active-music-pause-sync-adoption",
                    title: "TV first pause mirrors faster",
                    detail: "Apple TV now adopts an active-reader Apple Music bed pause on the same event pass, so a first Siri Remote pause has less room to stop only the bed while sentence narration keeps playing."
                ),
                AppChangelogEntry(
                    id: "acquisition-default-fanout-bounds-remote-fetches",
                    title: "Default discovery fetches less",
                    detail: "Default sources discovery now keeps full local, manual-download, and NAS freshness checks while limiting remote provider pages to the remaining visible budget plus a one-result probe, reducing over-fetch for Web and Apple Create."
                ),
                AppChangelogEntry(
                    id: "tvos-music-pause-adoption-pulse",
                    title: "TV pause mirrors immediately",
                    detail: "Apple TV now publishes a reader-pause adoption pulse when the Apple Music bed receives the first remote pause, so Job and Library playback pause sentence narration from the same event instead of waiting for a later transport callback."
                ),
                AppChangelogEntry(
                    id: "tvos-music-pause-adopts-during-autoresume",
                    title: "TV first pause owns narration",
                    detail: "Apple TV now adopts a system-observed Apple Music bed pause as reader transport even while normal bed auto-resume intent is set, so one remote press can pause both music and sentence narration."
                ),
                AppChangelogEntry(
                    id: "apple-device-update-launch-watch",
                    title: "Device update can launch-watch",
                    detail: "The default Apple device update target now carries the selected profile/device and honors the configured launch console timeout, giving physical deploys the same post-install crash-watch evidence as the explicit launch helper."
                ),
                AppChangelogEntry(
                    id: "apple-reader-transport-duplicate-window-cleanup",
                    title: "Duplicate command window stays centralized",
                    detail: "Job and Library playback no longer keep private duplicate-window adapters; both surfaces use the shared transport duplicate policy while the resolver owns the actual timing window."
                ),
                AppChangelogEntry(
                    id: "apple-reader-transport-pause-guard-resolver",
                    title: "Reader pause guards are shared",
                    detail: "Job and Library playback now route broker-echo suppression, blocked resume, and reinforced pause decisions through the shared transport resolver, reducing Apple TV Music-bed drift during device testing."
                ),
                AppChangelogEntry(
                    id: "apple-reader-transport-force-resolver",
                    title: "TV transport force decisions are shared",
                    detail: "Job and Library playback now share the resolver logic that decides when Apple TV should force reader pause or resume after a Music-bed pause, keeping both entry points aligned for Living Room testing."
                ),
                AppChangelogEntry(
                    id: "apple-reader-transport-echo-resolver",
                    title: "Reader transport echo handling is shared",
                    detail: "Job and Library playback now route direct Now Playing play-echo rejection through the shared reader transport resolver, keeping future Apple TV and iPad music-bed fixes aligned across both entry points."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-resume-echo-guard",
                    title: "TV Now Playing resume is less sticky",
                    detail: "Direct Apple TV Now Playing play commands now reject only short post-pause echoes, not the long-lived reader-owned paused-bed state, so resume can restart sentence audio and the Apple Music bed after the guard expires."
                ),
                AppChangelogEntry(
                    id: "tvos-broker-resume-bypasses-pause-hold",
                    title: "TV resume accepts the next click",
                    detail: "Apple TV Play/Pause broker resume now bypasses the short MusicKit pause-hold only for an accepted physical remote press, so a reader-owned paused bed can resume on the next click without loosening Now Playing echo protection."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-resume-defers-stale-pause",
                    title: "Music bed resume resists stale pause",
                    detail: "Reader-owned Apple Music bed resume now defers transient non-playing evidence while auto-resume is active, preventing a stale MusicKit pause observation from immediately pausing narration again."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-e2e-focus-controls",
                    title: "TV music-bed test controls are steadier",
                    detail: "The tvOS music-bed simulator journey now treats player containers as presence anchors and walks the debug control strip by remote focus order, so unattended tests reach the Play/Pause assertions instead of failing on a non-focusable view."
                ),
                AppChangelogEntry(
                    id: "tvos-broker-resume-accepts-paused-bed",
                    title: "TV broker resume accepts paused bed",
                    detail: "Apple TV Play/Pause broker handling now treats a fully paused reader-owned Apple Music bed as resumable after the short local hold, instead of swallowing the next remote press as a pause echo."
                ),
                AppChangelogEntry(
                    id: "apple-initial-track-mode-before-autoplay",
                    title: "Autoplay uses selected tracks",
                    detail: "iPad and iPhone book autoplay now attaches the audio-mode manager and synchronizes visible track selection before the first sentence prepare, preventing original-only startup until a tap refreshes playback."
                ),
                AppChangelogEntry(
                    id: "tvos-reader-resume-hold-tightened",
                    title: "TV resume clears sooner",
                    detail: "Apple TV reader pause still filters duplicate MusicKit echoes, but the pause hold now expires before the next accepted remote press so resume can restart sentence narration and the Apple Music bed together."
                ),
                AppChangelogEntry(
                    id: "tvos-sleep-launch-retry",
                    title: "Cinema wake retry is scripted",
                    detail: "Unattended tvOS deploys now detect the CoreDevice foreground-launch sleep refusal, request one userspace reboot, wait for the device to return, and retry launch once."
                ),
                AppChangelogEntry(
                    id: "changed-tests-run-contracts-before-simulators",
                    title: "Changed tests fail later",
                    detail: "Changed-test automation now runs non-Xcode contract gates before Apple simulator builds, so an unhealthy macOS account/cache state cannot hide useful Apple pipeline failures."
                ),
                AppChangelogEntry(
                    id: "apple-tv-resume-post-guard-play",
                    title: "TV resume needs one press",
                    detail: "Apple TV resume after a reader-owned Apple Music pause now accepts the first post-guard play command instead of treating the normal paused-bed state as an unsolicited echo."
                ),
                AppChangelogEntry(
                    id: "apple-host-readiness-json-report",
                    title: "Deploy blockers leave evidence",
                    detail: "Apple device host readiness now writes a token-safe JSON report for passed or failed local Xcode/CoreDevice account-cache checks, and device commands resolve friendly CoreDevice names such as Cinema before preflight, install, verify, or launch."
                ),
                AppChangelogEntry(
                    id: "apple-reader-pause-narration-first",
                    title: "TV pause favors the reader first",
                    detail: "Apple TV, iPad, and Now Playing reader pause paths now stop sentence narration before adopting the Apple Music bed pause, so MusicKit follow-up events cannot leave only the bed paused on the first command."
                ),
                AppChangelogEntry(
                    id: "apple-device-host-readiness-gate",
                    title: "Device deploys check the Mac first",
                    detail: "Apple device deploys now fail fast when the local macOS user and cache lookup is unhealthy, reporting the uid/passwd remediation before CoreDevice or Xcode can abort."
                ),
                AppChangelogEntry(
                    id: "apple-device-host-readiness-target",
                    title: "Cinema deploy readiness is explicit",
                    detail: "The repo now exposes make apple-device-host-readiness as a no-device deploy-host gate for Cinema TV, iPad, and iPhone testing while keeping device listing available for diagnostics."
                ),
                AppChangelogEntry(
                    id: "apple-template-delete-response-sync",
                    title: "Template deletes stay synced",
                    detail: "Apple Create now decodes the shared template-delete response and removes the canonical backend template id locally, keeping saved-template cleanup aligned with Web and backend routes."
                ),
                AppChangelogEntry(
                    id: "tvos-observed-music-pause-idempotent",
                    title: "TV Music-only pause is steadier",
                    detail: "Apple TV now avoids re-pausing the Apple Music bed after MusicKit has already adopted an observed Music-only pause as reader transport, and the simulator journey drives that path before the remote-button sequence."
                ),
                AppChangelogEntry(
                    id: "tvos-observed-pause-after-play-window",
                    title: "TV pause stops after resume",
                    detail: "Apple TV now treats observed Apple Music pauses after reader play as stale only for a short echo window, so a later real pause from the Music surface can still pause sentence narration on the first command."
                ),
                AppChangelogEntry(
                    id: "apple-reader-immediate-music-bed-pause",
                    title: "TV pause stops both tracks",
                    detail: "Apple TV and Apple reader playback now immediately adopts a MusicKit bed pause as reader transport before pausing narration, so the first remote or menu pause should stop both the bed and sentence track together."
                ),
                AppChangelogEntry(
                    id: "apple-reader-stale-requested-resume",
                    title: "Reader resume needs one press",
                    detail: "iPad and Apple reader Space/play resume now treats stale requested-but-paused narration as resume intent and reasserts playback once, reducing the case where the first key press only clears transport state."
                ),
                AppChangelogEntry(
                    id: "web-book-sparse-discovery-template",
                    title: "Web book templates match Create",
                    detail: "Web Narrate Ebook templates now also preserve sparse discovery provider and query state before a candidate is selected, matching Apple Create for Default sources and manual-download searches without storing candidate tokens."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-ebook-sparse-discovery-template",
                    title: "Book templates keep discovery",
                    detail: "Apple Narrate EPUB templates now preserve discovery provider and query state even before a candidate is selected, keeping Apple-saved drafts aligned with Web Default sources and manual-download discovery without storing candidate tokens."
                ),
                AppChangelogEntry(
                    id: "tvos-reader-pause-stale-avplayer-flags",
                    title: "TV pause catches stale player state",
                    detail: "Apple TV now mirrors a reader-owned Music pause into sentence narration even when AVPlayer requested or playing flags are transiently stale, so the first Siri Remote click should pause both the bed and the track."
                ),
                AppChangelogEntry(
                    id: "apple-sequence-sticky-lookup-resume",
                    title: "Lookup resume keeps narration",
                    detail: "Apple sequence playback now preserves validated reader play intent across lookup pronunciation and audio-session handoffs, reader-pause toggles resume before stale audio flags can pause again, and Apple TV adopts active-reader Music pauses before transient bed recovery."
                ),
                AppChangelogEntry(
                    id: "apple-autoplay-sentence-settle-resume",
                    title: "Autoplay waits for the sentence",
                    detail: "Book autoplay now keeps retrying until the rendered sentence matches the requested resume sentence, and reader-owned resume reasserts the narration audio session before restarting after lookup pronunciation."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-transient-dip-recovery",
                    title: "TV autoplay keeps going",
                    detail: "Apple TV now treats unprompted Apple Music non-playing events during active narration as recoverable bed dips instead of reader pause commands, preventing autoplay from stopping after a word."
                ),
                AppChangelogEntry(
                    id: "tvos-reader-resume-echo-window",
                    title: "TV resume responds sooner",
                    detail: "The Apple TV reader pause path keeps the reader-owned hold, ignores noisy broker echoes separately, and treats paused-bed pause callbacks as resume intent once the hold expires so lookup-bubble and remote resume do not get swallowed."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-immediate-observed-pause",
                    title: "TV pause stops narration immediately",
                    detail: "Apple TV adopted observed Apple Music stops immediately during active reader narration, removing the confirmation delay that let sentence audio keep playing briefly after Music paused."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-active-narration-pause-adoption",
                    title: "TV pause catches Music-only stops",
                    detail: "Apple TV Music-bed pause now treats a tvOS-observed Apple Music stop during active reader narration as reader pause intent even if the prior bed-evidence flag was cleared, closing the case where one Play/Pause press paused only Music while sentence audio continued."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-weak-signal-e2e",
                    title: "TV Music pause probe is stricter",
                    detail: "The tvOS Music-bed debug probe now simulates the weaker physical-device signal where Music stops before the reader command arrives, so unattended testing covers Music-only pause adoption."
                ),
                AppChangelogEntry(
                    id: "apple-source-label-readiness",
                    title: "Source readiness is stricter",
                    detail: "Apple Create readiness now documents and validates acquisition provider source labels so reusable device-pipeline checks catch provider-registry drift before simulator or device runs."
                ),
                AppChangelogEntry(
                    id: "manual-download-source-label-count",
                    title: "Manual download wording is accurate",
                    detail: "Manual-download discovery guidance now chooses folder vs folders from configured roots while keeping source paths limited to readable roots, so a single missing import folder is described accurately."
                ),
                AppChangelogEntry(
                    id: "apple-source-provider-labels",
                    title: "Create explains missing sources",
                    detail: "Backend acquisition providers now advertise source labels such as Books root, NAS video root, and Manual download folders, and Web plus Apple Create use those labels in unavailable-source guidance."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-pause-adoption",
                    title: "Apple TV pause adopts Music",
                    detail: "Apple TV reading-bed pause now accepts tvOS-observed Apple Music pause events as reader transport pauses, so one remote Play/Pause press can stop both Apple Music and sentence narration instead of pausing only the bed."
                ),
                AppChangelogEntry(
                    id: "apple-reader-progress-pill-e2e",
                    title: "Reader progress pill is guarded",
                    detail: "The integrated book header progress pill now keeps the chapter and played/remaining time stack readable inside the banner, and the Apple playback journey verifies the pill is present and populated after opening a book."
                ),
                AppChangelogEntry(
                    id: "apple-reader-full-book-progress-tv-pause",
                    title: "Reader progress and TV pause tighten",
                    detail: "Book headers now compute percent from the full content-index sentence range instead of the selected job window, and Apple TV interactive playback sends active Play/Pause presses through the full reader pause path so narration and Apple Music bed stop together."
                ),
                AppChangelogEntry(
                    id: "apple-translation-only-absolute-gates",
                    title: "Translation-only sync holds",
                    detail: "Translation-only word highlighting now keeps backend sentence gates in translation-audio time after slider jumps, so measured player duration drift cannot rescale the active translated sentence away from narration."
                ),
                AppChangelogEntry(
                    id: "apple-translation-timeline-runtime-highlights",
                    title: "Translation highlights follow audio",
                    detail: "Translation-only word highlighting now renders through the canonical timeline runtime after slider jumps, so if AVPlayer's actual file duration differs from gate metadata the next translated sentence does not reveal too early or drift away from narration."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-combined-time-local",
                    title: "Translation-only slider keeps local time",
                    detail: "Translation-only playback now keeps render timing on the active translation file even when the selected option is the combined original/translation pair, so slider jumps and next/previous skips no longer add the hidden original-track offset."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-anchor-renders-slider-target",
                    title: "Slider jumps keep the target rendered",
                    detail: "Translation-only slider seeks now let the recent single-track target pin transcript rendering and selected-sentence state until live audio reaches that sentence, preventing stale chunk-edge audio from making the next skip jump a 10-sentence batch."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-slider-seek-settles",
                    title: "Slider seeks wait for the target",
                    detail: "Translation-only slider jumps now keep a single-track file from autoplaying before the target sentence seek finishes, and narration is muted while the seek settles so translated word highlights do not drift or look like a 10-sentence skip."
                ),
                AppChangelogEntry(
                    id: "apple-slider-target-chunk-live-unlock",
                    title: "Slider jumps ignore stale audio",
                    detail: "Translation-only slider jumps now keep their target chunk locked until that chunk's audio reaches the requested sentence window, so old batch audio cannot unlock rendering or make the next skip jump by 10 sentences."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-slider-seek-guard",
                    title: "Slider skips stay in lockstep",
                    detail: "Translation-only slider and skip seeks now share a stale-completion guard and resolve explicit anchors through chunk-local rows, so dragging the slider cannot leave narration on one sentence while rendering or next/previous jumps by a 10-sentence batch."
                ),
                AppChangelogEntry(
                    id: "apple-start-only-gates-render-live",
                    title: "Translation-only slider keeps highlights",
                    detail: "Translation-only rendering now treats start-only sentence gates as absolute audio positions, so slider jumps keep translated word highlighting and narration on the same sentence even when job metadata omits end gates."
                ),
                AppChangelogEntry(
                    id: "apple-slider-cross-chunk-anchor",
                    title: "Slider skips stay sentence-sized",
                    detail: "Translation-only slider jumps now keep their cross-chunk sentence anchor while target metadata loads, so the next or previous command advances one sentence instead of falling through to the next 10-sentence chunk."
                ),
                AppChangelogEntry(
                    id: "apple-slider-commits-single-track-anchor",
                    title: "Slider commits keep their sentence",
                    detail: "Translation-only slider commits now refresh the shared single-track sentence anchor before the async seek begins, so the next or previous command starts from the slider target instead of stale playback time."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-slider-normalizes-local-rows",
                    title: "Slider skips stay on the next row",
                    detail: "iPad translation-only slider jumps now normalize backend chunk-local sentence rows before seeking, so next and previous advance one visible sentence instead of jumping a 10-sentence batch."
                ),
                AppChangelogEntry(
                    id: "apple-chunk-range-slider-identity",
                    title: "Translation slider uses sentence numbers",
                    detail: "Translation-only slider jumps, skips, bookmarks, and header progress now derive visible sentence numbers from each chunk range, preventing 10-sentence batch jumps when chunk metadata has local row ids."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-mode-beats-stale-sequence",
                    title: "Translation-only skips stay single-track",
                    detail: "Single-track Original or Translation mode now wins over stale sequence-controller state, so a slider jump followed by next or previous sentence stays on the visible track instead of skipping a 10-sentence batch."
                ),
                AppChangelogEntry(
                    id: "tvos-progress-slider-single-owner",
                    title: "Apple TV slider moves once",
                    detail: "Apple TV Interactive Reader now lets the focused footer scrubber own left and right remote presses, while the outer focus handler only moves up or down, preventing duplicate sentence-slider commits."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-slider-anchor-skips",
                    title: "Slider skips stay sentence-sized",
                    detail: "Translation-only slider jumps now keep their explicit sentence anchor through skip fallbacks, so the next or previous command moves one sentence instead of falling back to a stale chunk-level audio position."
                ),
                AppChangelogEntry(
                    id: "ipad-slider-jump-restores-live-highlighting",
                    title: "Slider jumps keep word highlights",
                    detail: "iPad translation-only slider jumps now release the temporary rendered-sentence lock as soon as the live audio sentence catches up, restoring word highlighting after scrubbing."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-pause-cancels-recovery",
                    title: "Apple TV pause stops both layers",
                    detail: "Apple TV reader transport now cancels delayed narration recovery retries when a pause is accepted and treats tvOS-delivered Apple Music pause events as reader pauses while the bed is active, so one Play/Pause press should stop both bed music and sentence audio."
                ),
                AppChangelogEntry(
                    id: "apple-slider-jump-locks-rendered-sentence",
                    title: "Slider jumps render the target",
                    detail: "Apple sentence slider jumps now temporarily lock the rendered transcript and header to the requested sentence until the audio playhead catches up, preventing translation-only jumps from showing a stale sentence while narration has moved."
                ),
                AppChangelogEntry(
                    id: "apple-audio-menu-syncs-single-track-mode",
                    title: "Audio menu keeps track sync",
                    detail: "Interactive Reader Audio menu choices now route Original, Translation, and Combined through the same audio-mode manager as text and header toggles, so iPad and Apple TV translation-only playback keeps sentence rendering, slider progress, skips, and narration on the selected track."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-timing-authority",
                    title: "Single-track rendering follows the selected track",
                    detail: "Original-only and translation-only reader modes now ignore stale AVPlayer URLs from the previous track while resolving sentence timing, keeping single-track rendering aligned with narration through track and chunk switches."
                ),
                AppChangelogEntry(
                    id: "apple-menu-text-toggle-syncs-audio",
                    title: "Menu text toggles keep audio aligned",
                    detail: "The Interactive Reader text-track menu now uses the same synchronized path as keyboard and header toggles, so choosing a single visible translation track also switches narration timing/audio to that track."
                ),
                AppChangelogEntry(
                    id: "apple-single-track-combined-queue-guard",
                    title: "Single-track playback keeps time",
                    detail: "Original-only and translation-only reader modes no longer treat multi-file combined audio as a queued mix, so sentence rendering, skips, and slider jumps stay on the selected track instead of adding the hidden other-track offset."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-passive-pause-recovery",
                    title: "Apple TV avoids false Music-bed pauses",
                    detail: "Apple TV now treats passive MusicKit non-playing observations during active narration as recoverable bed interruptions instead of immediate reader pauses, reducing cases where normal playback pauses both bed music and sentence audio."
                ),
                AppChangelogEntry(
                    id: "apple-media-chunk-order-runtime-contract",
                    title: "Media chunk order is checked",
                    detail: "Apple Settings and readiness checks now require the backend Media contract to advertise sentence-range chunk ordering, so stale runtimes are caught before device playback testing."
                ),
                AppChangelogEntry(
                    id: "apple-translation-only-chunk-order",
                    title: "Translation-only playback stays ordered",
                    detail: "Apple playback now sorts backend chunk manifests by sentence range before building next/previous navigation, so TV and iPad translation-only tracks advance from 2219 to the 2220 batch instead of following parallel generation order."
                ),
                AppChangelogEntry(
                    id: "lookup-resume-reclaims-reader-audio-session",
                    title: "Lookup resume keeps narration",
                    detail: "Interactive Reader now force-reasserts the reader audio session after lookup pronunciation before resuming, so Apple Music bed resume is less likely to leave sentence narration silent."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-shorter-guard-window",
                    title: "Apple TV remote resumes sooner",
                    detail: "Apple TV Music-bed Play/Pause now tests a 1.5-second reader-owned pause guard so deliberate resume should feel quicker while still blocking duplicate remote callbacks."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-quick-resume-window",
                    title: "Apple TV remote resumes faster",
                    detail: "Apple TV keeps a shorter duplicate-event guard after a Music-bed pause, but no longer waits through the old twelve-second hold before a deliberate second Play/Pause press can resume narration and bed music."
                ),
                AppChangelogEntry(
                    id: "tvos-broker-play-pause-echo-guard",
                    title: "Apple TV pause stays paused",
                    detail: "Apple TV reader playback now ignores the app-level Play/Pause broker echo that can follow a foreground remote pause, so the first press leaves narration and Apple Music bed paused instead of immediately resuming."
                ),
                AppChangelogEntry(
                    id: "tvos-shell-play-pause-now-playing-return",
                    title: "Apple TV menu Play returns to playback",
                    detail: "When Apple TV is back at the browse menu with a Now Playing target, the Play/Pause remote key now reopens the active job or library item through the same resume path as the Now Playing return control."
                ),
                AppChangelogEntry(
                    id: "tvos-music-bed-transport-resume",
                    title: "Apple TV remote resume is unblocked",
                    detail: "Apple TV reader transport now keeps a Music-bed duplicate-event guard while allowing a deliberate second Play/Pause press to resume narration and bed music together."
                ),
                AppChangelogEntry(
                    id: "tvos-menu-exits-playback",
                    title: "Apple TV Menu exits playback",
                    detail: "Apple TV Menu/Return now leaves interactive and video playback once overlays are closed instead of using the back button as a hidden paused-playback resume command."
                ),
                AppChangelogEntry(
                    id: "ipad-bubble-enter-lookup-e2e",
                    title: "iPad bubble Enter lookup is tested",
                    detail: "The iPad Music-bed journey now presses Enter while a lookup pronunciation bubble is open and verifies the reader receives a bubble lookup command before Space resumes playback."
                ),
                AppChangelogEntry(
                    id: "apple-journey-runner-enter-fallback",
                    title: "Enter tests use the working input path",
                    detail: "Apple journeys now drive Return and Enter through the hidden text-input fallback path, while raw Left and Right stay on XCTest typeKey events because raw XCTest Enter does not reliably reach the app."
                ),
                AppChangelogEntry(
                    id: "ipad-bubble-raw-arrow-e2e",
                    title: "iPad bubble arrows use real keys",
                    detail: "The iPad Music-bed E2E journey now presses raw XCTest Left and Right arrow keys while a lookup pronunciation bubble is open, exercising the same shortcut stack as a hardware keyboard."
                ),
                AppChangelogEntry(
                    id: "apple-journey-runner-raw-arrows",
                    title: "Apple journeys can press arrows",
                    detail: "The shared Apple journey runner now maps raw Left and Right keyboard steps through XCTest typeKey on iPad, with validator coverage so arrow-key journeys stay honest."
                ),
                AppChangelogEntry(
                    id: "ipad-bubble-arrow-e2e-coverage",
                    title: "iPad bubble arrows are guarded",
                    detail: "The iPad music-bed journey now presses Left and Right while a lookup pronunciation bubble is open and verifies the highlighted word actually moves before Space resumes playback."
                ),
                AppChangelogEntry(
                    id: "ipad-bubble-word-navigation-e2e-status",
                    title: "Bubble key failures are visible",
                    detail: "DEBUG playback controls now expose bubble word-navigation counters for simulator gates, and journey validation only allows Left/Right probes when explicit E2E controls back them."
                ),
                AppChangelogEntry(
                    id: "ipad-bubble-resume-simulator-proof",
                    title: "iPad bubble resume is tested",
                    detail: "The iPad music-bed simulator journey now starts from a lookup pronunciation pause and resumes with Space through the shared reader transport, proving sentence audio and Apple Music bed return together before device retest."
                ),
                AppChangelogEntry(
                    id: "ipad-bubble-resume-hidden-e2e-trigger",
                    title: "iPad E2E trigger stays out of the reader",
                    detail: "The DEBUG lookup-bubble resume probe now runs through the existing hidden E2E controls instead of adding a tappable overlay inside the reader surface, avoiding layout and focus side effects during normal playback."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-resume-preserves-track-position",
                    title: "iPad resume keeps its place",
                    detail: "iPad reader Play/Space now preserves the current sentence track and playhead on resume by trying the existing AVPlayer before any sentence-boundary recovery reload."
                ),
                AppChangelogEntry(
                    id: "ipad-apple-music-reader-resume-race",
                    title: "iPad Music bed stops cancelling resume",
                    detail: "iPad reader Play/Space with Apple Music bed now clears the reader-owned Music pause state before narration restarts, preventing MusicKit queue restore latency from immediately pausing the sentence track again."
                ),
                AppChangelogEntry(
                    id: "ipad-same-sentence-autoplay-resume",
                    title: "iPad Space restarts the current sentence",
                    detail: "iPad reader sentence resume now carries the autoplay intent through same-sentence sequence jumps, so Space/play retries on the already-rendered sentence restart narration instead of clearing the jump silently."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-requested-silent-recovery",
                    title: "iPad Space recovers silent resumes",
                    detail: "iPad reader transport recovery now treats actual playback as the success signal, so a Space resume that leaves narration requested but silent keeps reloading the current sentence until audio is playing again."
                ),
                AppChangelogEntry(
                    id: "ipad-paused-keyboard-selection-anchored",
                    title: "iPad paused keys stay anchored",
                    detail: "iPad reader Space resume now uses the reader transport recovery path directly, and paused Left/Right word navigation keeps its lookup sentence and token selection anchored instead of snapping back to stale playback progress."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-space-resume-retry",
                    title: "iPad Space resume is guarded",
                    detail: "iPad reader Space-bar resume now retries through the normal sentence-start path if AVPlayer clears the narration request immediately after an accepted play command, and the Music-bed simulator journey verifies Space pause and resume before device deployment."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-space-resume-after-pause",
                    title: "iPad Space resumes playback",
                    detail: "iPad and iPhone reader Play/Pause now allow an explicit Space-bar resume immediately after a reader-owned pause, while Apple TV keeps the longer Music-bed pause-hold guard for duplicate remote events."
                ),
                AppChangelogEntry(
                    id: "ipad-apple-music-bed-neutral-mix-session",
                    title: "iPad Music bed mixes again",
                    detail: "Apple Music reading beds now use a neutral playback audio session while mixing with sentence narration, keeping exclusive spoken-audio mode only when Apple Music is not the bed so iPad can play both layers together."
                ),
                AppChangelogEntry(
                    id: "ipad-apple-music-bed-deferred-recovery",
                    title: "iPad Music bed avoids false pauses",
                    detail: "iPad and iPhone Apple Music reading beds now keep transient sentence-boundary non-playing observations out of the reader-pause adoption path, while still recovering the bed if MusicKit remains stopped."
                ),
                AppChangelogEntry(
                    id: "ipad-apple-music-bed-transition-settle-only",
                    title: "iPad Music bed stays continuous",
                    detail: "iPad and iPhone Apple Music reading beds now treat sequence sentence handoffs as settle-only transitions when narration remains requested, avoiding a fresh MusicKit resume task at every sentence boundary."
                ),
                AppChangelogEntry(
                    id: "ipad-apple-music-bed-transient-pause-deferral",
                    title: "iPad Music bed rides through handoffs",
                    detail: "iPad Apple Music reading beds now defer transient MusicKit non-playing observations while narration is active, and the simulator gate asserts both the already-playing auto-resume path and a requested sentence-transition pause where Music must stay playing."
                ),
                AppChangelogEntry(
                    id: "ipad-apple-music-bed-transition-resume-short-circuit",
                    title: "iPad Music bed transitions stay quiet",
                    detail: "Interactive Reader now short-circuits Apple Music bed auto-resume before scheduling a MusicKit task when the system player is already playing, and DEBUG music-bed gates expose the already-playing skip count for device checks."
                ),
                AppChangelogEntry(
                    id: "ipad-apple-music-bed-idempotent-resume",
                    title: "iPad Music bed stops blipping",
                    detail: "Apple Music reading beds now treat automatic resume as idempotent when MusicKit is already playing under the reader, so iPad sentence changes no longer nudge the system player and briefly dip the background track."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-session-stability-evidence",
                    title: "Music bed session is testable",
                    detail: "Job and Library playback now switch reader narration into Apple Music mixing mode as soon as Apple Music becomes the bed, and the automated music-bed journey verifies playback stays on the stable mixing session instead of repeatedly reactivating audio at playback boundaries."
                ),
                AppChangelogEntry(
                    id: "ipad-apple-music-bed-session-cache",
                    title: "iPad Music bed stays steady",
                    detail: "Interactive Reader now skips redundant AVAudioSession category reactivation when Apple Music mixing is already configured, preventing the Music bed from dipping briefly on every sentence transition while preserving reader-owned playback controls."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-rejected-play-repause",
                    title: "TV Music pause rejects stray play",
                    detail: "Apple TV reader-owned Music-bed transport now actively re-pauses the Apple Music bed and sentence narration when a rejected play callback arrives during the reader pause guard, covering system remote deliveries that already nudged Music before the app rejected the resume."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-first-press-gate",
                    title: "TV Music pause gate is stricter",
                    detail: "The tvOS Music-bed simulator journey now requires the first remote Play/Pause press to show both reader narration and Apple Music paused before any resume attempt, tightening coverage for the two-click pause regression."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-owned-state-hard-pause",
                    title: "TV Music bed pauses from ownership",
                    detail: "Apple TV Play/Pause now hard-pauses whenever the reader still owns the Apple Music bed, even if tvOS has already flickered the instantaneous Music playing flags, so a stale status sample cannot turn the remote press into a resume."
                ),
                AppChangelogEntry(
                    id: "acquisition-default-result-eligibility",
                    title: "Create default results stay explicit",
                    detail: "Web Video Dubbing and Apple YouTube Dub now filter Default sources result lists through the backend provider default-eligibility contract too, keeping direct YouTube URL candidates out of blind default results while preserving explicit URL review."
                ),
                AppChangelogEntry(
                    id: "acquisition-default-eligibility-contract",
                    title: "Create defaults are backend-owned",
                    detail: "Backend acquisition providers now advertise which media kinds may participate in default discovery fan-out, and Web and Apple Create use that shared contract so direct YouTube URL review stays explicit while NAS, manual, YouTube search, and indexer defaults remain consistent."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-idempotent-pause",
                    title: "TV Music pause stays idempotent",
                    detail: "Apple TV reader-owned Music-bed transport now keeps explicit pause callbacks as pause during the reader pause hold, while Play and toggle still resolve through reader state, so duplicate remote deliveries cannot turn a fresh pause into resume."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-pauses-on-owned-bed-state",
                    title: "TV Music bed pause matches lookup",
                    detail: "Apple TV Play/Pause now enters the same reader-owned pause path used by lookup/read-aloud whenever the app still owns an Apple Music bed, even if the system playback status has already flickered while the pause is settling."
                ),
                AppChangelogEntry(
                    id: "apple-tv-play-pause-hard-pause-route",
                    title: "TV Play/Pause uses hard pause",
                    detail: "Apple TV Play/Pause now uses the lookup-bubble hard-pause semantics when narration or the system Apple Music bed is actually playing, bypassing stale toggle inference before pausing both layers."
                ),
                AppChangelogEntry(
                    id: "prepared-artifact-provenance-create-state",
                    title: "Create source memory is cleaner",
                    detail: "Web and Apple Create now merge prepared artifact provenance into saved book and video discovery state, so templates keep normalized source provider, acquisition provider, candidate id, and source kind after local handoffs."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-suppress-before-publish",
                    title: "TV Music stray play is swallowed",
                    detail: "Apple TV Music-bed pause now suppresses stray MusicKit play or track-change observations before publishing a playing state to the reader, matching the lookup-bubble hard-pause path more closely."
                ),
                AppChangelogEntry(
                    id: "apple-music-bed-reader-pause-autoresume-guard",
                    title: "TV Music pause stays paused",
                    detail: "Apple Music reading beds now treat reader-owned pause like lookup-bubble pause: auto-resume and disappear handoff paths stay blocked while the reader transport pause is latched, so only an explicit reader play command can restart the bed."
                ),
                AppChangelogEntry(
                    id: "subtitle-template-source-mode-parity",
                    title: "Subtitle templates round-trip",
                    detail: "Apple-saved subtitle creation templates now use Web's canonical existing-source mode, and Web accepts older Apple server-mode subtitle templates as existing-file templates so saved Create settings round-trip across surfaces."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-jump-supersession",
                    title: "Reader jumps stay ordered",
                    detail: "Apple Interactive Reader sentence jumps now ignore stale same-chunk metadata completions after a newer slider, search, bookmark, or chapter jump supersedes them, preventing older pending jumps from clearing the newer target while audio moves ahead of the rendered transcript."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-direct-callback-state",
                    title: "TV Music remote uses reader state",
                    detail: "Apple TV reader-owned Music-bed playback now resolves direct tvOS Now Playing play/pause callbacks through reader state while Apple Music is only the bed, so a hardware Play/Pause delivery that arrives as an explicit play command still enters the same pause path that stops sentence audio and the Music bed together."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-foreground-pause-guard",
                    title: "TV Music pause holds steady",
                    detail: "Apple TV reader-owned Music-bed pauses now route remote Play/Pause through both the foreground command and app broker paths, then hold reader resumes locally during the pause window so duplicate tvOS or Now Playing deliveries cannot restart sentence audio while Apple Music is still settling under the reader surface."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-remote-e2e",
                    title: "TV remote sync is tested",
                    detail: "The Apple TV Music-bed simulator journey now drives the Siri Remote path without debug-button shortcuts and reads status without moving TV focus, proving guarded pause, post-hold resume, rapid double-press pause, and return-to-menu behavior in one credentialed run."
                ),
                AppChangelogEntry(
                    id: "local-manual-epub-placeholder-discovery-skip",
                    title: "Create hides empty EPUBs",
                    detail: "Web and Apple Create discovery now skip zero-byte EPUB placeholders in backend books roots and manual download folders, keeping unfinished browser or NAS handoffs out of Narrate Ebook source pickers until a real file is present."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-reader-pause-latch",
                    title: "TV Music pause latches first",
                    detail: "Apple TV reader-owned Music-bed pauses now latch Apple Music before publishing sentence pause state, and book lookup/read-aloud pauses use the same reader-transport latch so bubble activation does not depend on MusicKit observation timing."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-stale-toggle-guard",
                    title: "TV Music toggles stay guarded",
                    detail: "Apple TV reader-owned Music-bed pauses now ignore stale non-foreground Now Playing callbacks that resolve to play, including delayed toggle callbacks, while the foreground remote Play/Pause path stays covered by the reader pause duplicate window."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-guarded-toggle-e2e",
                    title: "TV Music toggle guard is tested",
                    detail: "The Apple TV Music-bed simulator journey now includes an E2E-only guarded-toggle control, proving stale command-center toggles do not increment reader transport or resume audio while the pause guard is active."
                ),
                AppChangelogEntry(
                    id: "create-intake-readiness-threadpool",
                    title: "Create readiness stays responsive",
                    detail: "Apple and Web Create intake readiness now snapshots backend queue pressure through the API threadpool hook, keeping readiness checks responsive while backend worker state is busy."
                ),
                AppChangelogEntry(
                    id: "apple-tv-play-pause-single-owner",
                    title: "TV Play/Pause stays singular",
                    detail: "Apple TV interactive playback now lets the outer reader transport own Play/Pause when a book shell supplies the unified override, avoiding a second embedded toggle that could restart narration or the Apple Music bed after a pause."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-observed-pause-e2e",
                    title: "TV Music pause path is tested",
                    detail: "The Apple TV Music-bed simulator journey now drives the observed Apple Music pause path directly, proving the reader pause guard arms without a reader transport command before the remote-button sequence continues."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-immediate-pause-adoption",
                    title: "TV Music pause adopts immediately",
                    detail: "Apple TV now treats an observed Apple Music pause during active reader narration as a reader pause immediately, closing a bounce window where Music could resume before the pause guard was armed."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-play-callback-guard",
                    title: "TV Music pause ignores stray play",
                    detail: "Apple TV reader-owned Music-bed pauses now ignore stray Now Playing play callbacks while the pause guard is active, keeping Music-surface events from restarting sentence playback after a remote pause."
                ),
                AppChangelogEntry(
                    id: "apple-tv-remote-play-pause-log-evidence",
                    title: "TV Play/Pause logs prove routing",
                    detail: "Apple TV Music-bed launch-log checks now require the app-level remote Play/Pause broker breadcrumb and the unified reader-owned pause adoption breadcrumb, making physical remote failures easier to diagnose."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-observed-pause-adoption",
                    title: "TV Music pause guard is unified",
                    detail: "Apple TV Music-bed pauses observed from the system Music surface now adopt the same reader-owned pause guard as explicit reader pauses, keeping fullscreen Music suppression, stale resume cancellation, and pause confirmation active together."
                ),
                AppChangelogEntry(
                    id: "apple-tv-remote-play-pause-broker",
                    title: "TV Play/Pause uses app broker",
                    detail: "Apple TV remote Play/Pause now also routes through the app-level player shortcut broker, matching the iPad Space/keyboard path when SwiftUI focus or MusicKit surfaces do not deliver the view-scoped command."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-sequence-pause-cancel",
                    title: "TV Music pause stops stale resumes",
                    detail: "Apple TV reader-owned Music-bed pause now cancels pending sentence sequence handoffs before pausing audio, preventing stale track-switch callbacks from restarting narration immediately after Play/Pause."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-reader-pause-surface-reclaim",
                    title: "TV Music pause owns the reader",
                    detail: "Apple TV Music-bed pause now treats a system-level Apple Music pause during active narration as a reader pause, keeps the reader Now Playing surface alive while paused, and holds fullscreen Music fanart suppression until the reader resumes."
                ),
                AppChangelogEntry(
                    id: "apple-e2e-auth-token-bootstrap",
                    title: "E2E can use auth tokens",
                    detail: "Apple simulator E2E config can now launch with E2E_AUTH_TOKEN or EBOOKTOOLS_SESSION_TOKEN, validate the token through the normal session endpoint, and fall back to username/password only when needed."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-quiet-pause-suppression",
                    title: "TV Music pause stays quiet",
                    detail: "Apple TV Music-bed Play/Pause now stops reader Now Playing reassertion loops while paused, and bed resume keeps fullscreen Music artwork suppression active so Apple Music remains underneath narration instead of retaking the screen."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-explicit-command-idempotence",
                    title: "TV Music pause stays explicit",
                    detail: "Apple TV reader-owned Music-bed controls now keep direct Now Playing play and pause commands idempotent while reserving current-state resolution for foreground Play/Pause and true toggle callbacks, reducing pause-then-resume loops and fullscreen Music fanart takeovers."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-suppression-window",
                    title: "TV Music fanart guard holds",
                    detail: "Apple TV reader-owned Music-bed pause now keeps fullscreen-art suppression pulses alive beyond the pause guard, and the queue-preserving suppression path is named clearly so Music does not regain the playback surface."
                ),
                AppChangelogEntry(
                    id: "apple-reader-transport-policy-shared",
                    title: "Reader transport policy is shared",
                    detail: "Job and Library playback now resolve Apple TV Music-bed Play/Pause commands through the same shared transport policy, keeping reader-owned remote behavior consistent across Browse surfaces."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-command-center-toggle",
                    title: "TV Music bed remote toggles reader",
                    detail: "Apple TV now treats Play and Pause command-center callbacks as state-resolved reader toggles while Apple Music is only the background bed, matching the physical remote and keeping fullscreen Music fanart suppression active."
                ),
                AppChangelogEntry(
                    id: "apple-browse-smart-row-cues",
                    title: "Browse rows show ready cues",
                    detail: "Apple Library, Jobs, and search rows now mirror Web's smart row cues by showing Newly completed for fresh playable entries and Needs attention for missing media when no resume evidence is present."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-explicit-pause-commands",
                    title: "TV Music pause stays reader-owned",
                    detail: "Apple TV reader Now Playing keeps MusicKit play or track-change callbacks during a reader-owned pause re-paused before Music can resume narration or promote fullscreen fanart."
                ),
                AppChangelogEntry(
                    id: "apple-reader-timing-provenance-pill",
                    title: "Reader timing source is visible",
                    detail: "Apple interactive reader headers now show a compact Timing provenance pill for job-level, chunk-level, or gate-only timing data, matching the Web reader's timing-source visibility without adding another control."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-fullscreen-watchdog",
                    title: "TV Music fanart stays blocked",
                    detail: "Apple TV now keeps fullscreen Music artwork suppression on a live watchdog while Apple Music is only the reading bed, force-reapplying the tvOS idle block if MusicKit playback or track changes reset it."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-dub-template-discovery-ui-restore",
                    title: "YouTube Dub templates restore source search",
                    detail: "Applying an Apple YouTube Dub template now restores the saved discovery source and search query in the native source picker, so reviewed Web-style video discovery context is visible before saving or handing off again."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-dub-template-discovery-query",
                    title: "YouTube Dub templates keep discovery",
                    detail: "Apple YouTube Dub templates now preserve the selected discovery source and search query with reviewed video candidates, matching Web template handoff behavior for NAS, manual download, YouTube, and indexer discovery."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-queue-preserving-suppression",
                    title: "TV Music fanart stays suppressed",
                    detail: "Apple TV reader-owned Music-bed pause now keeps the Apple Music queue intact while repeatedly re-pausing stray Music playback and holding reader Now Playing suppression, so fullscreen Music artwork has less chance to take over and resume can restart both transports together."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-discovery-review-fields",
                    title: "Create templates keep review details",
                    detail: "Apple Narrate EPUB discovery templates now preserve reviewed title, rights, language, year, and capability hints when templates move between Apple and Web Create."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-stale-resume-cancel",
                    title: "TV Music pause stays paused",
                    detail: "Apple TV Music-bed Play/Pause now cancels stale async MusicKit resume tasks after reader pause and delays tvOS Music surface release briefly, so a quick pause does not resurrect Music or sentence playback from an older resume."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-observed-pause",
                    title: "TV Music pause mirrors reader",
                    detail: "Apple TV Music-bed Play/Pause now treats observed Apple Music pauses during bed auto-resume intent as reader pauses, clears stale Now Playing remote handlers, and releases the tvOS Music playback surface faster to reduce fullscreen fanart takeovers."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-discovery-context",
                    title: "Create templates keep discovery",
                    detail: "Apple Narrate EPUB saved templates now preserve the Discovery query and selected provider, including Default sources, so Web-style discovery drafts reopen with their source-search context."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-delayed-surface-release",
                    title: "TV Music pauses hold steady",
                    detail: "Apple TV Music-bed Play/Pause now shares the reader fullscreen-artwork suppression guard and delays Music surface release until a reader pause has held, improving pause/resume consistency while still pushing Music fanart away."
                ),
                AppChangelogEntry(
                    id: "apple-create-discovery-autoload",
                    title: "Create discovery opens ready",
                    detail: "Apple Narrate EPUB Discovery now auto-loads available default source results when the Discovery panel opens or the provider changes, matching the Web dialog while keeping manual search available."
                ),
                AppChangelogEntry(
                    id: "acquisition-discovery-read-only-defaults",
                    title: "Create discovery is safer",
                    detail: "Video source discovery now skips incomplete .part downloads without renaming files, and Default sources hides explicit-only YouTube URL candidates unless that source is selected directly."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-duplicate-resume-hold",
                    title: "TV Music pause holds",
                    detail: "Apple TV Music-bed Play/Pause now blocks delayed duplicate resume callbacks briefly after reader pause and lets the watchdog re-pause narration before the Music guard returns."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-stale-resume-guard",
                    title: "TV Music resume races are blocked",
                    detail: "Apple TV Music-bed Play/Pause now rejects stale async MusicKit resume tasks after a reader pause and reapplies the tvOS fullscreen artwork suppression guard during reader Now Playing reassertions."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-releases-music-surface",
                    title: "TV Music artwork releases",
                    detail: "Apple TV reader-owned Apple Music pauses now release the tvOS Music playback surface after the pause has held instead of immediately tearing down the queue, while preserving the remembered bed selection so reader Play/Pause can resume the bed from the app."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-direct-command-e2e",
                    title: "TV direct command checks run",
                    detail: "The Apple TV Music-bed simulator journey now taps debug-only reader play and pause command buttons, proving direct Now Playing callbacks resolve through reader state instead of only testing physical remote toggles."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-direct-command-toggle",
                    title: "TV remote callbacks resolve state",
                    detail: "Apple TV reader playback now treats direct remote play and pause callbacks as state-resolved toggles, so a stray Music or Now Playing play command cannot consume the duplicate window and block the real reader-owned pause."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-remote-dedup",
                    title: "TV Music remote presses stay singular",
                    detail: "Apple TV reader playback now resolves Play/Pause intent before mutating state and suppresses duplicate foreground/Now Playing callbacks from the same remote press, so the Music bed cannot immediately resume a reader-owned pause."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-fullscreen-suppression",
                    title: "TV Music artwork stays suppressed",
                    detail: "Apple TV now keeps the reader surface active while Apple Music is only a background bed, including paused reader transport, and disables tvOS idle promotion into full-screen Music artwork during that reader-owned state."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-guard-e2e-status",
                    title: "TV Music guard is testable",
                    detail: "The Apple TV Music-bed simulator journey now exposes and asserts the reader pause guard directly, so unattended runs prove remote pause enters the fullscreen-fanart suppression state and remote play clears it."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-pause-guard-extended",
                    title: "TV Music pause guard holds",
                    detail: "Apple TV reader-owned Music-bed pauses now treat the pause-hold window as a hard suppression state, so stray MusicKit play observations are re-paused instead of restarting narration or surfacing Music artwork."
                ),
                AppChangelogEntry(
                    id: "web-reader-timing-provenance-pill",
                    title: "Web timing provenance is visible",
                    detail: "Web interactive playback now shows a compact timing provenance pill when word sync is active, distinguishing job-level estimated timing from chunk metadata timing so QA can spot inferred-token playback faster."
                ),
                AppChangelogEntry(
                    id: "apple-tv-music-bed-reader-pause-surface",
                    title: "TV Music bed follows reader pause",
                    detail: "Apple TV Music-bed playback now treats reader Play/Pause as the durable owner: stray Apple Music resumes are re-paused until the reader resumes, and active narration keeps tvOS from drifting into full-screen Music artwork."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-27",
            dateLabel: "June 27, 2026",
            version: "2026.06.27.001",
            entries: june27Entries
        ),
        AppChangelogDay(
            id: "2026-06-26",
            dateLabel: "June 26, 2026",
            version: "2026.06.26.183",
            entries: june26Entries
        ),
        AppChangelogDay(
            id: "2026-06-25",
            dateLabel: "June 25, 2026",
            version: "2026.06.25.109",
            entries: [
                AppChangelogEntry(
                    id: "apple-create-discovery-source-panel",
                    title: "Create discovery is easier to reach",
                    detail: "Apple Narrate EPUB now presents server EPUB selection and discovery as explicit source modes, Web Narrate Ebook mirrors that Source and Discovery split inside the source step, and interactive reader word taps in sequence playback switch language tracks when needed before rewinding to the tapped word."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-slider-draft-word-lookup",
                    title: "Reader slider and word taps stay live",
                    detail: "Apple interactive reader sentence sliders now clear stale draft positions when keyboard skips, jumps, bookmarks, chapters, search, or word taps move playback, and paused word taps rewind to the word, stay paused, and open lookup."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-slider-layout-sync",
                    title: "Reader slider stays in sync",
                    detail: "Apple interactive reader headers now reserve space for the sentence slider so the original track does not render underneath it, and the slider follows the active playback sentence instead of a stale manual selection."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-sentence-slider-word-taps",
                    title: "Reader jumps feel like media controls",
                    detail: "Apple interactive reader headers now include a sentence progress slider for fast jumps, word taps seek and play from the tapped word, double taps seek, pause, and open lookup, and sequence next/previous follows original-to-translation playback order."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-jump-input-submit",
                    title: "Jump input and bookmarks land cleanly",
                    detail: "Apple interactive reader Jump To input now sanitizes numeric entry, clamps to available sentence bounds, offers keyboard Done and Go actions on iPad and iPhone, and bookmark jumps prefer stored chunk/time targets before falling back to sentence lookup."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-time-pill-tap",
                    title: "Header time pill and bookmarks respond",
                    detail: "Apple interactive reader headers now preserve the timeline tap action after moving progress and time pills inside the iPad book identity banner, and book bookmark adds update immediately during playback before backend reconciliation."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-progress-integrated",
                    title: "Reader header uses the full iPad row",
                    detail: "Apple interactive reader headers now carry the progress and time pills inside the book identity banner on iPad, let the header fill the available width, and open a book metadata overlay when the cover is tapped on iPad or iPhone."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-generic-hardening",
                    title: "Book-job headers avoid device crashes",
                    detail: "Apple interactive reader headers now avoid fit-based generic SwiftUI alternatives in the book-job overlay, reducing physical-device metadata instantiation pressure when opening older library jobs."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-device-crash-fix",
                    title: "Book loading is stable on iPad",
                    detail: "Apple interactive reader headers now choose their wide or compact identity-banner layout through explicit platform branching, avoiding a SwiftUI generic metadata crash seen on physical iPad when opening book jobs."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-job-label",
                    title: "Book templates keep job labels",
                    detail: "Apple-saved generated-book and Narrate EPUB templates now include trimmed title and job_label metadata, matching submitted Apple book jobs so Web handoff and template reuse show the same book title label."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-identity-banner-adaptive-layout",
                    title: "Reader header adapts more cleanly",
                    detail: "Apple interactive reader headers now give the identity banner a wide and compact layout, keeping the book cover, title, author, metadata pills, and inline controls composed across iPhone, iPad, Apple TV, and Mac Designed for iPad."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-cover-url",
                    title: "Book templates keep remote covers",
                    detail: "Apple-saved generated-book and Narrate EPUB templates now preserve remote cover artwork as cover_url in Web-compatible book_metadata, while local/backend cover files stay in book_cover_file just like submitted Apple book jobs."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-book-genres",
                    title: "Book templates keep genre lists",
                    detail: "Apple-saved generated-book and Narrate EPUB templates now include normalized book_genres arrays in their Web-compatible book_metadata, matching submitted Apple book jobs and preserving genre metadata through Web handoff and template reuse."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-book-language",
                    title: "Book templates keep language metadata",
                    detail: "Apple-saved generated-book and Narrate EPUB templates now include source-language metadata in their Web-compatible book_metadata, keeping Apple-to-Web draft handoff and later Apple template reuse aligned with submitted book jobs."
                ),
                AppChangelogEntry(
                    id: "apple-create-book-metadata-template-parity",
                    title: "Book templates carry metadata better",
                    detail: "Apple Create saved-template metadata loading now treats Web book_metadata JSON as a shared metadata source, keeping book-only Narrate Ebook templates useful across Apple surfaces."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-identity-component",
                    title: "Reader header is easier to verify",
                    detail: "Apple interactive reader headers now route the banner, book cover, title, metadata pills, and inline controls through a dedicated SwiftUI identity banner component with stable UI-test identifiers across Apple surfaces."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-chapter-end-placeholder",
                    title: "Chapter ranges are clearer",
                    detail: "Apple Narrate EPUB chapter controls now show a Same as start end-chapter placeholder, making loaded chapter ranges and manual-range fallback states easier to read across Apple surfaces."
                ),
                AppChangelogEntry(
                    id: "apple-offline-export-row-busy-state",
                    title: "Offline exports stay row-focused",
                    detail: "Apple Jobs and Library now track offline export busy state per source row, preventing duplicate export taps for the active item without blocking export actions for other completed jobs or library entries."
                ),
                AppChangelogEntry(
                    id: "video-discovery-template-roundtrip",
                    title: "Video templates keep discovery context",
                    detail: "Web Video Dubbing and Apple YouTube Dub now restore token-free video discovery provenance when applying saved templates, so reviewed NAS, manual download, YouTube search, and indexer context survives apply/save loops."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-full-header-composition",
                    title: "Reader header feels unified",
                    detail: "Apple interactive playback now treats the full header as one media identity area: the banner carries the channel mark, book cover, title, author, item and model pills, plus controls, while progress pills adapt beside or below it without redundant outer chrome."
                ),
                AppChangelogEntry(
                    id: "video-discovery-template-provenance",
                    title: "Video discovery context survives templates",
                    detail: "Web Video Dubbing and Apple YouTube Dub templates now keep token-free discovery provenance for reviewed NAS, manual download, YouTube search, and indexer candidates, including provider, candidate id, selected paths, rights, and source kind without saving candidate tokens."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-banner-cover-pill-polish",
                    title: "Reader headers feel more native",
                    detail: "Apple interactive and video playback headers now present the banner, cover art, title, author, and info pills as one media identity area with stronger material styling, cover fallbacks, and fit-aware metadata rows across Apple surfaces."
                ),
                AppChangelogEntry(
                    id: "apple-create-download-station-autoselect",
                    title: "Downloader results become selectable faster",
                    detail: "Apple YouTube Dub now matches completed Download Station filenames against the refreshed manual-download candidates and applies the matching video/subtitle source, reducing the handoff from indexer result to native job setup."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-identity-polish",
                    title: "Reader header identity is clearer",
                    detail: "Apple interactive playback now treats the banner, book cover, title, author, type, and model pills as one media identity block, with a fallback cover tile and fit-aware pills across iPhone, iPad, Apple TV, and Mac Designed for iPad."
                ),
                AppChangelogEntry(
                    id: "download-station-handoff-metadata-tolerance",
                    title: "Downloader handoff is more tolerant",
                    detail: "Web and Apple video discovery now recognize Download Station handoff metadata when the backend sends explicit providers, booleans, or legacy string flags, keeping reviewed indexer candidates visible across metadata encoding changes."
                ),
                AppChangelogEntry(
                    id: "apple-create-indexer-handoff-readiness",
                    title: "Create preflights indexer handoff",
                    detail: "Apple Create readiness now reports whether the backend registry can hand searchable Newznab/Torznab video candidates to Download Station, separating provider inventory health from the downloader handoff path used by Web and Apple discovery."
                ),
                AppChangelogEntry(
                    id: "apple-reader-identity-banner",
                    title: "Reader header feels more composed",
                    detail: "Apple interactive playback now groups the banner, book cover, title, author, item type, translation model, and controls into a modern media-style identity header with stable spacing across iPhone, iPad, Apple TV, and Mac Designed for iPad."
                ),
                AppChangelogEntry(
                    id: "acquisition-download-station-handoff-provider",
                    title: "Indexer handoff is clearer",
                    detail: "Web Video Dubbing and Apple YouTube Dub now use an explicit Download Station handoff marker from backend discovery candidates, keeping sensitive indexer URLs server-side while showing the reviewed handoff path in discovery results."
                ),
                AppChangelogEntry(
                    id: "apple-reader-header-lookup-speech-polish",
                    title: "Reader chrome feels more native",
                    detail: "Apple interactive playback now uses a translucent media-style header with unified control pills, and lookup read-aloud keeps the tapped track language and voice so target-language words are spoken correctly."
                ),
                AppChangelogEntry(
                    id: "apple-playback-diagnostics-compact-warning",
                    title: "Playback diagnostics are quieter",
                    detail: "Apple playback no longer shows the upper file, chunk, audio, timing, and image count strip; iPhone, iPad, Apple TV, and Mac Designed for iPad only show a compact warning when media gaps could affect playback."
                ),
                AppChangelogEntry(
                    id: "apple-browse-header-without-sync-strip",
                    title: "Browse headers are quieter",
                    detail: "Apple Library, Jobs, and combined search no longer show the redundant upper browse action row; section, search, and filter controls move to the top of the list, while resume sync and logout live in Settings."
                ),
                AppChangelogEntry(
                    id: "apple-video-sleep-timer",
                    title: "Video playback shares the sleep timer",
                    detail: "Apple video playback now uses the same sleep timer pill as interactive reading on iPhone, iPad, Apple TV, and Mac Designed for iPad; timer expiration pauses video playback, and TV remote focus moves through Search, Bookmarks, Sleep Timer, and timeline controls."
                ),
                AppChangelogEntry(
                    id: "apple-interactive-sleep-timer",
                    title: "Interactive playback adds a sleep timer",
                    detail: "Apple interactive playback now has a sleep timer pill with 5, 15, 30, and 45 minute presets on iPhone, iPad, Apple TV, and Mac Designed for iPad; when it expires, narration and the active reading bed pause together."
                ),
                AppChangelogEntry(
                    id: "apple-playback-diagnostics-warning-only",
                    title: "Playback chrome is quieter",
                    detail: "Apple playback now hides the media diagnostics file, chunk, timing, audio, and image count strip during healthy playback and only surfaces it when diagnostics report media gaps."
                ),
                AppChangelogEntry(
                    id: "apple-now-playing-cache-reset",
                    title: "Lock-screen timing resets cleanly",
                    detail: "Apple Now Playing now resets cached elapsed-time and duration state when playback metadata is cleared, so the next book or video republishes complete timing to lock-screen controls."
                ),
                AppChangelogEntry(
                    id: "apple-playback-pills-without-language-flags",
                    title: "Playback jump pills stay visible",
                    detail: "Apple interactive playback now keeps Jump, Search, and Bookmark controls visible across iPhone, iPad, Apple TV, and Mac Designed for iPad even when a book has no language flag metadata."
                ),
                AppChangelogEntry(
                    id: "apple-sentence-image-prefetch",
                    title: "Sentence images prefetch nearby",
                    detail: "Apple interactive playback now prefetches nearby sentence images around the active transcript position, so image-heavy book chunks feel smoother when revisited or advanced through quickly."
                ),
                AppChangelogEntry(
                    id: "apple-token-normalization-cache",
                    title: "Chunk revisits are lighter",
                    detail: "Apple interactive playback now reuses a bounded token normalization cache across live refreshes and chunk metadata rebuilds, making repeated chunk visits lighter without retaining stale sentence metadata."
                ),
                AppChangelogEntry(
                    id: "apple-bookmark-time-jump-ready-seek",
                    title: "Bookmark jumps wait for playback",
                    detail: "Apple interactive playback now defers time-based bookmark jumps until the target chunk audio is ready, so jumping from the bookmark pill preserves active playback on iPhone, iPad, Apple TV, and Mac Designed for iPad."
                ),
                AppChangelogEntry(
                    id: "apple-live-media-initial-fallback",
                    title: "Active job playback is more tolerant",
                    detail: "Apple Job playback still prefers live media for running jobs, but now falls back to the regular media snapshot if the first live-media request is temporarily unavailable."
                ),
                AppChangelogEntry(
                    id: "apple-audio-stream-recovery",
                    title: "Narration recovers from short stream failures",
                    detail: "Apple narration playback now retries one failed stream at the current file/time position and cleans up stall observers during player rebuilds, improving recovery from brief network interruptions."
                ),
                AppChangelogEntry(
                    id: "apple-timing-token-sanitization",
                    title: "Transcript timing is smoother",
                    detail: "Apple interactive playback now validates backend word timing windows before highlighting, dropping invalid timings and clamping overlaps inside each sentence/file group so reading stays fluid even with imperfect metadata."
                ),
                AppChangelogEntry(
                    id: "apple-transcript-metadata-retry",
                    title: "Transcript loading can be retried",
                    detail: "Apple interactive playback now records retryable chunk metadata failures and shows a transcript Retry action that reloads metadata and prepares audio again on iPhone, iPad, Apple TV, and Mac Designed for iPad."
                ),
                AppChangelogEntry(
                    id: "apple-playback-search-bookmark-focus",
                    title: "Playback search and bookmarks are easier to reach",
                    detail: "Apple playback now gives Search and Bookmark pills stable test identifiers and keeps the Apple TV video header focus path moving between Search, Bookmarks, and timeline controls while preserving jump-to-result and jump-to-bookmark behavior."
                ),
                AppChangelogEntry(
                    id: "apple-create-epub-picker-filter",
                    title: "Narrate EPUB choices stay book-focused",
                    detail: "Apple Narrate EPUB now filters server source choices to real EPUB paths and sorts them newest-first on device, matching the Web default picker while keeping manual-path fallback available."
                ),
                AppChangelogEntry(
                    id: "ipad-lookup-arrow-space-reliability",
                    title: "iPad keyboard playback controls are steadier",
                    detail: "Paused lookup bubbles now keep Left/Right and Ctrl+Left/Ctrl+Right on word navigation before sentence transport, while Space remains on the shared play/pause dispatch path after lookup read-aloud focus changes."
                ),
                AppChangelogEntry(
                    id: "apple-video-discovery-prepared-selection",
                    title: "Video discovery uses prepared sources",
                    detail: "Apple YouTube Dub now prepares NAS and manual video discovery candidates through the shared acquisition artifact endpoint before filling video and subtitle paths, matching the safer Narrate EPUB handoff."
                ),
                AppChangelogEntry(
                    id: "indexer-candidate-download-station-ui",
                    title: "Indexer handoff stays server-side",
                    detail: "Web Video Dubbing and Apple YouTube Dub can now send a selected Newznab/Torznab result to Download Station through the server-side candidate token, keeping API-key URLs hidden while the user confirms the task."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-audio-session-retry",
                    title: "TV lookup Read Aloud is reachable",
                    detail: "Apple TV lookup bubbles now cycle remote focus across visible controls so Read Aloud can be selected, then retry pronunciation audio-session setup with simpler playback options if tvOS rejects the richer spoken-audio session."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-epub-output-follows-source",
                    title: "Narrate EPUB names follow the selected book",
                    detail: "Apple Narrate EPUB now refreshes the output/job name when the selected EPUB changes unless that output field was manually edited, preventing new jobs from inheriting another book's name."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-empty-audio-fallback",
                    title: "TV lookup avoids empty pronunciation audio",
                    detail: "Apple TV lookup read-aloud now rejects decoded-but-empty backend pronunciation audio and immediately falls back to platform speech, so the Read Aloud control does not go silent."
                ),
                AppChangelogEntry(
                    id: "lookup-pronunciation-audio-decode-fallback",
                    title: "Lookup audio falls back instead of going silent",
                    detail: "Apple lookup read-aloud now falls back to platform speech when backend pronunciation audio cannot start, so Apple TV, iPhone, iPad, and voice previews do not fail silently."
                ),
                AppChangelogEntry(
                    id: "lookup-read-aloud-audio-handoff",
                    title: "Lookup read-aloud gets a clear audio lane",
                    detail: "Apple TV and iPhone/iPad lookup read-aloud now pauses active playback before speaking, and cached narration playback stops pronunciation audio before resuming the book or video track."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-read-aloud-retry",
                    title: "TV lookup can speak again",
                    detail: "Apple TV lookup bubbles now include an explicit Read Aloud control that replays the current lookup through backend pronunciation with platform speech fallback, matching the selected source or translation track."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-pronunciation-language-fallback",
                    title: "TV read-aloud avoids silent language misses",
                    detail: "Apple TV lookup read-aloud now keeps a platform speech fallback even when the selected lookup language is a backend label that cannot be mapped to a specific AVSpeech voice code."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-pronunciation-timeout",
                    title: "TV lookup read-aloud is more reliable",
                    detail: "Apple TV lookup pronunciation now falls back to platform speech after a short backend timeout and keeps speech playback on the main actor, so slow backend TTS no longer leaves lookup audio silent."
                ),
                AppChangelogEntry(
                    id: "lookup-cache-permission-fallbacks",
                    title: "Lookup cache permissions are clearer",
                    detail: "Lookup-cache endpoints now preserve authorization failures while missing caches still fall back gracefully to live MyLinguist lookup in Web and Apple playback."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-epub-settings-selected-source",
                    title: "Chapter loading shows the selected book",
                    detail: "Narrate EPUB now resolves the selected server EPUB through one shared helper, so the right-side Job Settings chapter controls show the same selected-book detail as the source picker."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-epub-picker-context",
                    title: "EPUB choices are easier to trust",
                    detail: "Apple Narrate EPUB keeps the server picker usable for manual-path fallback, adds folder context to nested NAS EPUB choices, and shows which selected server book Load Chapters will query."
                ),
                AppChangelogEntry(
                    id: "post-export-timing-validation",
                    title: "Timing validation is recorded",
                    detail: "Generated chunk metadata now records post-export timing validation for original and translation tracks, making overlap and duration drift visible to Web and Apple playback diagnostics."
                ),
                AppChangelogEntry(
                    id: "tvos-lookup-button-provider-readiness",
                    title: "TV lookup and Create gates are steadier",
                    detail: "Apple TV lookup read-aloud controls now activate through native focusable buttons, and Apple Create readiness validates the backend acquisition provider registry before simulator journeys."
                ),
                AppChangelogEntry(
                    id: "video-discovery-provider-registry",
                    title: "Video discovery follows backend providers",
                    detail: "Web Video Dubbing and Apple YouTube Dub discovery now derive video-capable provider choices from the backend registry while preserving NAS, manual downloads, YouTube search, and Indexers ordering."
                ),
                AppChangelogEntry(
                    id: "apple-create-readiness-discovery-provider-policy",
                    title: "Create readiness checks discovery policy",
                    detail: "Apple Create readiness now opens Narrate EPUB discovery, selects the attended Z-Library provider from the backend-driven source picker, and asserts the disabled-policy message before continuing through language and media-job defaults."
                ),
                AppChangelogEntry(
                    id: "registry-driven-ebook-discovery-tv-read-aloud",
                    title: "Discovery and TV read-aloud are steadier",
                    detail: "Web and Apple ebook discovery now derive book-capable source choices from the backend registry while preserving familiar ordering and policy messages, and Apple TV lookup read-aloud configures the tvOS playback audio session before pronunciation."
                ),
                AppChangelogEntry(
                    id: "ebook-discovery-zlibrary-attended-import",
                    title: "Ebook discovery explains attended imports",
                    detail: "Web and Apple ebook discovery now show Z-Library as an attended-import-only path with direct automation disabled, guiding authorized EPUBs through Manual downloads or the backend books folder."
                ),
                AppChangelogEntry(
                    id: "apple-create-server-epub-picker-chapter-skip",
                    title: "Narrate EPUB source loading is clearer",
                    detail: "Apple Create keeps the server EPUB picker visible with a loaded-source summary and skips generated/runtime chapter lookups that cannot resolve through the backend EPUB folder."
                ),
                AppChangelogEntry(
                    id: "create-source-metadata-reset-tv-lookup-playback",
                    title: "Create metadata and TV lookup are steadier",
                    detail: "Narrate EPUB now clears stale source metadata when the selected book changes, chapter loading states are clearer, and Apple TV video lookup can play from cached narration timing again."
                ),
                AppChangelogEntry(
                    id: "create-discovery-prepare-handoff",
                    title: "Discovery sources use prepared handoff",
                    detail: "Web Narrate Ebook and Apple Narrate EPUB now ask the backend to prepare selected discovery artifacts before filling source paths, keeping local and acquired EPUB handoffs consistent."
                ),
                AppChangelogEntry(
                    id: "acquisition-artifact-prepare",
                    title: "Discovery sources prepare cleanly",
                    detail: "Reviewed discovery artifacts now resolve through a shared prepare endpoint, giving Web and Apple Create the same source fields for local EPUBs, acquired public EPUBs, and local video candidates."
                ),
                AppChangelogEntry(
                    id: "sentence-splitter-lowercase-dialogue",
                    title: "Sentence splits read more naturally",
                    detail: "Sentence splitting now recognizes lowercase starts and quoted dialogue after terminal punctuation while keeping ellipsis continuations and inline dialogue tags together; refined sentence caches invalidate with splitter version regex-v5."
                ),
                AppChangelogEntry(
                    id: "apple-openlibrary-provenance-payload",
                    title: "Catalog provenance stays with jobs",
                    detail: "Apple generated-book and Narrate EPUB submissions now preserve applied Open Library work IDs, edition IDs, lookup hints, and cover URLs in job metadata while keeping visible form edits authoritative."
                ),
                AppChangelogEntry(
                    id: "openlibrary-apply-metadata",
                    title: "Discovery applies book metadata",
                    detail: "Open Library discovery candidates can now fill Web Narrate Ebook metadata JSON and Apple Narrate EPUB metadata fields without choosing or acquiring an EPUB source."
                ),
                AppChangelogEntry(
                    id: "openlibrary-metadata-discovery",
                    title: "Open Library metadata joins Create",
                    detail: "Web Narrate Ebook and Apple Narrate EPUB can now search Open Library as a metadata-only source, showing reviewable catalog matches without attempting EPUB acquisition."
                ),
                AppChangelogEntry(
                    id: "internet-archive-acquire-contract",
                    title: "Public acquire contract is traced",
                    detail: "The shared acquisition route and Apple DTO checks now cover Internet Archive artifact responses, preserving source metadata such as the archive identifier after reviewed EPUB acquisition."
                ),
                AppChangelogEntry(
                    id: "ebook-discovery-provider-controls",
                    title: "Discovery providers scale better",
                    detail: "Web Narrate Ebook now renders ebook discovery sources from one provider descriptor list, and Apple Narrate EPUB uses a menu picker so Local, Manual, Gutenberg, and Internet Archive options stay readable."
                ),
                AppChangelogEntry(
                    id: "internet-archive-ebook-discovery",
                    title: "Public EPUB discovery expands",
                    detail: "Backend, Web Narrate Ebook, and Apple Narrate EPUB now search Internet Archive text items for ordinary downloadable EPUB files and acquire reviewed candidates into the shared server EPUB root."
                ),
                AppChangelogEntry(
                    id: "web-apple-indexer-discovery",
                    title: "Create surfaces search indexers",
                    detail: "Web Video Dubbing and Apple YouTube Dub can now search configured Newznab/Torznab indexer metadata as review-only candidates without filling playable source paths or exposing raw download URLs."
                ),
                AppChangelogEntry(
                    id: "newznab-torznab-review-discovery",
                    title: "Indexer discovery is safer",
                    detail: "The backend can now search configured Newznab/Torznab video indexers as review-only metadata, keeping API keys and raw download URLs server-side."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-dub-download-station-handoff",
                    title: "Apple Create queues Download Station",
                    detail: "Apple YouTube Dub can now submit authorized Download Station links or magnets, poll the shared acquisition job, and refresh manual-download/NAS sources when the task completes."
                ),
                AppChangelogEntry(
                    id: "web-video-download-station-handoff",
                    title: "Web Video queues Download Station",
                    detail: "Web Video Dubbing can now submit authorized Download Station source links or magnets, poll the shared task endpoint, and continue final file selection through manual-download discovery."
                ),
                AppChangelogEntry(
                    id: "sentence-splitter-smart-quotes-cache",
                    title: "Reading splits are steadier",
                    detail: "Sentence splitting now handles smart closing quotes and initials more fluidly, and content-index caches include splitter identity plus refined sentence hashes to avoid stale chapter ranges."
                ),
                AppChangelogEntry(
                    id: "download-station-acquisition-jobs",
                    title: "Download Station handoff starts",
                    detail: "The shared acquisition backend now exposes reviewed Download Station job submit and poll endpoints, keeping NAS credentials server-side while Apple and Web clients get a common task-status contract."
                ),
                AppChangelogEntry(
                    id: "apple-video-manual-download-discovery",
                    title: "Downloaded videos are easier to pick",
                    detail: "Apple YouTube Dub discovery can now search configured manual download folders for user-authorized NAS or Download Station video files and reuse discovered subtitle hints."
                ),
                AppChangelogEntry(
                    id: "apple-ebook-discovery-provider-readiness",
                    title: "Ebook source readiness is clearer",
                    detail: "Apple Narrate EPUB discovery now uses the shared acquisition provider registry to disable unavailable ebook source searches and explain missing backend source roots before showing an empty result list."
                ),
                AppChangelogEntry(
                    id: "apple-translation-timing-local-fallback",
                    title: "Translation highlights stay aligned",
                    detail: "Apple interactive playback now falls back to chunk-local translation timing tracks when job-level timing is unavailable, matching original-track highlighting for multi-sentence chunks."
                ),
                AppChangelogEntry(
                    id: "manual-download-discovery",
                    title: "Manual downloads are discoverable",
                    detail: "Apple and Web Narrate Ebook discovery can now search configured manual download folders for user-authorized EPUBs downloaded through Safari, Download Station, or another attended workflow."
                ),
                AppChangelogEntry(
                    id: "youtube-search-provider-errors",
                    title: "YouTube search errors are clearer",
                    detail: "YouTube acquisition discovery now returns token-safe quota, rate-limit, and authorization messages for configured providers instead of collapsing API failures into a generic provider error."
                ),
                AppChangelogEntry(
                    id: "youtube-search-provider-readiness",
                    title: "YouTube search readiness is visible",
                    detail: "Web and Apple YouTube search surfaces now read the token-safe acquisition provider registry, disable YouTube search when the backend is not configured, and keep direct URL or NAS paths usable."
                ),
                AppChangelogEntry(
                    id: "web-youtube-download-search-handoff",
                    title: "Web YouTube downloads search first",
                    detail: "Web YouTube downloads can now search configured YouTube metadata results from the backend, select a result into the existing URL field, and continue through subtitle inspection, subtitle selection, and video download review."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-search-discovery-handoff",
                    title: "Apple Create reviews YouTube search",
                    detail: "Apple YouTube Dub discovery can now switch between NAS videos and configured YouTube search metadata, routing selected YouTube results into the existing metadata review flow before any download or dubbing step."
                ),
                AppChangelogEntry(
                    id: "web-youtube-search-discovery-handoff",
                    title: "Web Video search reviews YouTube results",
                    detail: "Web Video Dubbing discovery can now switch between NAS videos and configured YouTube search metadata, routing selected YouTube results into the existing metadata review flow before any download or dubbing step."
                ),
                AppChangelogEntry(
                    id: "apple-gutenberg-discovery-handoff",
                    title: "Apple Create acquires public EPUBs",
                    detail: "Apple Narrate EPUB discovery can now switch between local EPUBs and Gutenberg catalog results, acquiring reviewed Gutenberg EPUBs before filling the standard server EPUB path."
                ),
                AppChangelogEntry(
                    id: "web-gutenberg-discovery-handoff",
                    title: "Web Create acquires public EPUBs",
                    detail: "Web Narrate Ebook discovery can now switch between local EPUBs and Gutenberg catalog results, acquiring reviewed Gutenberg EPUBs before filling the standard input path."
                ),
                AppChangelogEntry(
                    id: "gutenberg-reviewed-acquisition",
                    title: "Public EPUB acquisition added",
                    detail: "Reviewed Gutenberg candidates can now be acquired into the backend books root through the shared acquisition endpoint, with Web and Apple clients aware of the new handoff path."
                ),
                AppChangelogEntry(
                    id: "gutenberg-acquisition-discovery",
                    title: "Public ebook discovery added",
                    detail: "The backend now exposes Project Gutenberg/Gutendex as an explicit discovery provider, returning public catalog ebook metadata and EPUB links for reviewed acquisition."
                ),
                AppChangelogEntry(
                    id: "acquisition-discovery-contract-hardening",
                    title: "Discovery contract tightened",
                    detail: "Acquisition discovery now caps backend result limits, skips provider scans for zero-limit internal calls, and rejects providers that are not yet real discovery sources."
                ),
                AppChangelogEntry(
                    id: "apple-create-discovery-state-split",
                    title: "Discovery state stays scoped",
                    detail: "Apple Create now keeps EPUB and YouTube Dub discovery responses and errors separate, so switching modes cannot show stale book or video candidates."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-template-discovery-paths",
                    title: "Create templates restore videos",
                    detail: "Apple Create YouTube Dub templates now fall back to saved discovery-state video and subtitle paths, so Web-authored discovery templates reopen with the intended NAS selections."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-dub-video-discovery",
                    title: "Apple Create discovers videos",
                    detail: "Apple YouTube Dub now offers Discover Video Sources from the shared acquisition endpoint, filling existing NAS video and subtitle fields from backend-visible candidates."
                ),
                AppChangelogEntry(
                    id: "web-video-discovery-picker",
                    title: "Web Video Dubbing discovers NAS videos",
                    detail: "Web Video Dubbing now offers a Discover video sources panel backed by the shared acquisition endpoint, filling the existing video and subtitle selection from backend-visible NAS candidates."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-ebook-discovery-picker",
                    title: "Apple Create discovers EPUBs",
                    detail: "Apple Narrate EPUB now offers a Discover Sources control backed by the shared acquisition discovery endpoint, filling the existing server EPUB path from backend-visible local candidates."
                ),
                AppChangelogEntry(
                    id: "web-narrate-ebook-discovery-picker",
                    title: "Web Create discovers EPUBs",
                    detail: "Web Narrate Ebook now offers a Discovery sources dialog backed by the shared acquisition contract, filling the existing input path from local EPUB candidates without changing the job payload."
                ),
                AppChangelogEntry(
                    id: "acquisition-discovery-and-splitter-quotes",
                    title: "Discovery search starts",
                    detail: "The backend now exposes editor/admin source discovery for local EPUBs, NAS videos with subtitle hints, and configured YouTube metadata search, while sentence splitting preserves closing quotes after punctuation."
                ),
                AppChangelogEntry(
                    id: "acquisition-provider-contract",
                    title: "Discovery providers listed",
                    detail: "The backend now exposes a token-safe acquisition provider contract for local EPUBs, NAS videos, YouTube URL and search workflows, reviewed downloader handoff, and planned public or open ebook sources."
                ),
                AppChangelogEntry(
                    id: "sequence-playback-per-sentence-fallback",
                    title: "Sequence playback keeps sentences",
                    detail: "Web and Apple sequence playback now fills missing per-sentence gates from that sentence's phase durations, so mixed chunks keep every original and translation sentence in the plan."
                ),
                AppChangelogEntry(
                    id: "discovery-acquisition-plan",
                    title: "Discovery layer planned",
                    detail: "The shared pipeline now has a lawful discovery acquisition plan for YouTube search, NAS and Download Station handoff, public or open ebook catalogs, metadata enrichment, and Web/Apple Create source handoff."
                ),
                AppChangelogEntry(
                    id: "apple-original-timing-local-index",
                    title: "Original highlights align",
                    detail: "Apple interactive playback now reads chunk-local original timing tokens before legacy global fallback so iPad, iPhone, and Apple TV preserve per-word original highlights from chunk metadata."
                ),
                AppChangelogEntry(
                    id: "pipeline-llm-model-threadpool",
                    title: "Model picker stays responsive",
                    detail: "The shared pipeline LLM model inventory route now runs provider discovery on FastAPI's threadpool so Web and Apple Create model pickers do not block the async server."
                ),
                AppChangelogEntry(
                    id: "creation-template-delete-canonical-id",
                    title: "Draft cleanup ids align",
                    detail: "Saved creation-template deletes now return the canonical template id and skip storage reads for empty normalized ids, keeping Web and Apple draft cleanup predictable."
                ),
                AppChangelogEntry(
                    id: "release-contract-date-lock",
                    title: "Changelog date locked",
                    detail: "The release contract now requires the latest Markdown changelog day, Apple in-app changelog day, visible date label, and shipped release version to agree on today's build date."
                ),
                AppChangelogEntry(
                    id: "youtube-library-picker-token-reuse",
                    title: "Video picker loads lighter",
                    detail: "The shared YouTube NAS library picker now prefilters unrelated stored jobs by filename before path normalization and reuses discovered video tokens while building Web and Apple Create source rows."
                ),
                AppChangelogEntry(
                    id: "apple-create-shared-chapter-range-control",
                    title: "Create shares chapter controls",
                    detail: "Apple Create now uses one Narrate EPUB chapter-range control in both the source pane and wide job-settings pane, keeping Load Chapters, pickers, summaries, and sentence-window updates consistent."
                ),
                AppChangelogEntry(
                    id: "web-create-chapter-loading-pipeline-coverage",
                    title: "Create chapter gate expanded",
                    detail: "The shared Web pipeline now directly covers Narrate Ebook content-index chapter loading, generated-source skips, consecutive chapter selection, backend error surfacing, and estimated range and duration labels."
                ),
                AppChangelogEntry(
                    id: "apple-changelog-latest-version-contract",
                    title: "Changelog version stays current",
                    detail: "The Daily Changelog header now follows the latest changelog day, and the release contract requires that Swift day to match the shipped app release so today's version cannot silently drift."
                ),
                AppChangelogEntry(
                    id: "web-create-voice-inventory-pipeline-coverage",
                    title: "Create voice gate expanded",
                    detail: "The shared Web pipeline now directly covers Narrate Ebook backend voice inventory matching, region/base language-code normalization, per-language preview overrides, and inventory load failures."
                ),
                AppChangelogEntry(
                    id: "web-create-file-discovery-pipeline-coverage",
                    title: "Create source gate expanded",
                    detail: "The shared Web pipeline now directly covers Narrate Ebook server EPUB discovery, newest backend book defaults, generated-source skips, upload validation, and history-derived start defaults."
                ),
                AppChangelogEntry(
                    id: "web-job-settings-pipeline-coverage",
                    title: "Job settings gate expanded",
                    detail: "The shared Web pipeline now keeps book and subtitle job settings summaries covered alongside JobProgress rendering, stage health, and generated-file utilities."
                ),
                AppChangelogEntry(
                    id: "web-library-pipeline-coverage",
                    title: "Library pipeline gate expanded",
                    detail: "The shared Web pipeline now runs focused Library metadata, LibraryList helper, media cell, action, status badge, and resume badge coverage before the broader Vitest and build checks."
                ),
                AppChangelogEntry(
                    id: "apple-create-epub-picker-scoped-list",
                    title: "Create keeps EPUB choices",
                    detail: "Apple Create now trusts the backend-scoped EPUB list even when filename metadata omits the .epub suffix, so iPad, iPhone, and Apple TV server book pickers keep valid available books visible."
                ),
                AppChangelogEntry(
                    id: "apple-create-nas-epub-picker",
                    title: "Create finds NAS EPUBs",
                    detail: "Apple Create and Web source pickers now follow visible symlinked NAS folders and Apple chapter loading accepts zero-based backend chapter indexes, restoring server EPUB choices and Load Chapters for more book collections."
                ),
                AppChangelogEntry(
                    id: "apple-create-image-node-check",
                    title: "Create checks image nodes",
                    detail: "Apple Create generated-book image settings can now check configured image API nodes and show aggregate availability before submitting illustrated jobs."
                ),
                AppChangelogEntry(
                    id: "apple-create-infers-chapter-ends",
                    title: "Create loads chapter ranges",
                    detail: "Apple Create now infers missing chapter end sentences from the next chapter or total sentence count when loading a server EPUB index, preventing chapter selections from collapsing to a one-sentence range."
                ),
                AppChangelogEntry(
                    id: "apple-create-decodes-server-options",
                    title: "Create loads server options",
                    detail: "Apple Create now decodes backend Create option, EPUB picker, and chapter-index responses through the same snake-case strategy as the API client, restoring full language/default lists and backend-visible server books on iPad and iPhone."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-24",
            dateLabel: "June 24, 2026",
            version: "2026.06.24.27",
            entries: [
                AppChangelogEntry(
                    id: "apple-create-save-native-templates",
                    title: "Create saves templates",
                    detail: "Apple Create can now save current generated-book, Narrate EPUB, subtitle, and YouTube dubbing settings as reusable Web-compatible creation templates, then hand the selected template to Web Create."
                ),
                AppChangelogEntry(
                    id: "apple-web-template-handoff",
                    title: "Web handoff carries templates",
                    detail: "Apple Create now includes the selected saved creation template when opening Web Create, so iPad and iPhone can continue book, subtitle, and YouTube dubbing drafts in the advanced Web forms."
                ),
                AppChangelogEntry(
                    id: "apple-create-delete-saved-templates",
                    title: "Create manages templates",
                    detail: "Apple Create can now delete the selected saved creation template after confirmation, keeping Web-authored book, subtitle, and YouTube dubbing presets tidy from iPad, iPhone, and Apple TV."
                ),
                AppChangelogEntry(
                    id: "apple-create-nas-ebook-metadata",
                    title: "Create labels NAS books",
                    detail: "Apple Create now shows backend-visible EPUB size and modified date in the server book picker, making the latest NAS source easier to verify before starting Narrate EPUB jobs."
                ),
                AppChangelogEntry(
                    id: "apple-tvos-create-tuning-controls",
                    title: "TV Create gets tuning",
                    detail: "Apple TV Create now exposes subtitle typography, subtitle batch tuning, and YouTube dubbing mix, flush, and batch controls through remote-friendly value steppers."
                ),
                AppChangelogEntry(
                    id: "web-media-provider-defaults",
                    title: "Web media defaults align",
                    detail: "Web Subtitle Tool and Video Dubbing now use the same backend translation provider and transliteration defaults that Apple Create reads from /api/books/options."
                ),
                AppChangelogEntry(
                    id: "apple-create-media-default-readiness",
                    title: "Create checks media defaults",
                    detail: "Apple Create readiness now verifies that the backend advertises shared subtitle and YouTube dubbing processing defaults before simulator journeys run."
                ),
                AppChangelogEntry(
                    id: "apple-create-ass-server-sources",
                    title: "Create lists ASS subtitles",
                    detail: "Apple Create now keeps backend-visible ASS subtitle files selectable for subtitle jobs while still preferring SRT and VTT as default server sources when they are available."
                ),
                AppChangelogEntry(
                    id: "apple-create-right-pane-job-type",
                    title: "Create moves job type right",
                    detail: "On iPad and local Mac Designed for iPad, Apple Create now keeps the job type picker with the right-hand job settings pane so the left setup pane can stay focused on source and metadata."
                ),
                AppChangelogEntry(
                    id: "apple-create-advanced-metadata-json",
                    title: "Create edits full metadata",
                    detail: "Apple Create now gives subtitle and YouTube jobs an advanced metadata JSON editor, so iPad and iPhone can review and apply full nested metadata payloads in addition to the high-value native fields."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-source-labels",
                    title: "Generated books clarify sources",
                    detail: "Apple Create generated-book fields now label continuation context as source-book title, author, genre, and summary so it is clear what belongs to the existing book versus the new generated book."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-source-context",
                    title: "Generated books get source context",
                    detail: "Apple Create generated-book jobs now accept source-book title, author, genre, and summary context so iPad and iPhone can start continuation-style books with explicit source metadata."
                ),
                AppChangelogEntry(
                    id: "apple-device-update-preflight",
                    title: "Device updates preflight first",
                    detail: "The guarded Apple physical-device update helper now runs a non-mutating CoreDevice health preflight before confirmed installs, while keeping installed-app metadata verification as a separate post-install check."
                ),
                AppChangelogEntry(
                    id: "apple-offline-export-progress",
                    title: "Exports show progress",
                    detail: "Apple Jobs and Library now show a visible offline-export progress overlay while the backend prepares an offline player archive."
                ),
                AppChangelogEntry(
                    id: "apple-job-health-row",
                    title: "Jobs show running health",
                    detail: "Apple Jobs rows now show a compact running-job health line with the latest backend stage, elapsed runtime, and ETA from progress events."
                ),
                AppChangelogEntry(
                    id: "apple-create-opens-created-job",
                    title: "Create opens new jobs",
                    detail: "Apple Create now routes successful submissions directly to the created job in Jobs, selects the matching Jobs category, and starts Jobs auto-refresh so newly submitted book, subtitle, and video jobs are immediately visible."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-epub-history-settings",
                    title: "Narrate EPUB remembers settings",
                    detail: "Apple Create Narrate EPUB now reuses prior narration job audio, output, translation, transliteration, lookup-cache, and chunking settings while still preserving fields edited in the current form."
                ),
                AppChangelogEntry(
                    id: "apple-shared-pipeline-make-wrappers",
                    title: "Shared pipeline gets local commands",
                    detail: "The repo now exposes Make wrappers for the shared Apple device app pipeline contract, backend, source-sync, and non-physical shared preflight commands so ebook-tools can dogfood the reusable pipeline from its own checkout."
                ),
                AppChangelogEntry(
                    id: "apple-local-surface-verification-gate",
                    title: "Local Apple checks get one command",
                    detail: "The repo now has a single non-physical verification gate that runs Apple contracts and then compiles all local Apple surfaces before any attended physical-device update."
                ),
                AppChangelogEntry(
                    id: "apple-local-surface-build-gate",
                    title: "Local Apple builds get one gate",
                    detail: "The repo now has a single non-physical build gate that chains iPhone simulator, iPad simulator, Apple TV simulator, and local Mac Designed for iPad/iPhone compile checks before attended device deploys."
                ),
                AppChangelogEntry(
                    id: "apple-ios-simulator-build-lanes",
                    title: "Phone and iPad builds get gates",
                    detail: "The repo now has quick iPhone and iPad simulator compile lanes, plus a combined iOS simulator target, so pipeline dogfood can verify handheld and tablet builds without launching full journeys or touching physical devices."
                ),
                AppChangelogEntry(
                    id: "apple-tvos-simulator-build-lane",
                    title: "TV builds get a gate",
                    detail: "The repo now has a quick tvOS simulator compile lane for the Apple TV app, so pipeline dogfood can catch tvOS-only Swift regressions before a full journey run or physical-device deploy."
                ),
                AppChangelogEntry(
                    id: "apple-library-source-diagnostics",
                    title: "Library shows sources",
                    detail: "Apple Library rows now expose read-only Source Details on iPhone, iPad, and Apple TV with stored-source, file, type, path, status, and media diagnostics."
                ),
                AppChangelogEntry(
                    id: "apple-library-source-upload-review",
                    title: "Library reviews sources",
                    detail: "Apple Library source replacement now opens a review sheet before upload and accepts the same common book and video source extensions as Web."
                ),
                AppChangelogEntry(
                    id: "apple-create-ipad-job-settings-pane",
                    title: "Create shifts job settings",
                    detail: "iPad and local Mac Designed for iPad Create now keep generated-book sentence count plus Narrate EPUB output and sentence-range settings in the right-hand job settings pane instead of the left setup pane."
                ),
                AppChangelogEntry(
                    id: "apple-library-metadata-editor",
                    title: "Library edits metadata",
                    detail: "Apple Library rows on iPhone and iPad now expose an Edit Metadata sheet for title, author, genre, language, and ISBN, using the same backend PATCH contract as Web."
                ),
                AppChangelogEntry(
                    id: "apple-library-metadata-enrichment",
                    title: "Library enriches metadata",
                    detail: "Apple Library rows can now call the shared backend external metadata enrichment endpoint and refresh the row with the returned title, cover, genre, ISBN, and source details."
                ),
                AppChangelogEntry(
                    id: "apple-library-job-offline-export",
                    title: "Apple exports players",
                    detail: "Jobs and Library rows on Apple surfaces can now request the shared backend offline-player export zip and open the returned download URL, matching the Web export action for completed media."
                ),
                AppChangelogEntry(
                    id: "apple-create-ipad-wide-settings-pane",
                    title: "Create widens settings",
                    detail: "On iPad and local Mac Designed for iPad, Apple Create now keeps the navigation rail compact and reserves the wide right-hand detail area for language, narration, output, status, and submit settings."
                ),
                AppChangelogEntry(
                    id: "apple-create-tv-metadata-artwork",
                    title: "Create previews TV artwork",
                    detail: "Apple Create subtitle and YouTube TV metadata now show and edit TVMaze poster and episode-still artwork URLs, expose the YouTube thumbnail URL, and include TMDB and IMDb ID fields before submission."
                ),
                AppChangelogEntry(
                    id: "apple-create-metadata-cache-clear",
                    title: "Create clears metadata caches",
                    detail: "Apple Create now gives iPad job settings more of the right-hand detail area and adds subtitle, TV, and YouTube metadata cache clearing controls that use the shared backend runtime contract."
                ),
                AppChangelogEntry(
                    id: "apple-create-subtitle-metadata-lookup-name",
                    title: "Create edits metadata lookup",
                    detail: "Apple Create subtitle metadata lookup now exposes an editable lookup filename before Lookup or Refresh, matching the Web metadata loader for renamed or manually selected subtitle sources."
                ),
                AppChangelogEntry(
                    id: "apple-create-subtitle-metadata-preview",
                    title: "Create loads subtitle metadata",
                    detail: "Apple Create subtitle jobs can now load TV metadata before submission, edit job label, show, season, episode, title, and airdate fields on iPad, and send the enriched metadata JSON with the job."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-metadata-preview",
                    title: "Create loads video metadata",
                    detail: "Apple Create YouTube Dub can now load TV and YouTube metadata before submission, edit the key title, channel, series, and episode fields on iPad, and send the enriched metadata payload with the job."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-inline-subtitles",
                    title: "Create extracts subtitles",
                    detail: "Apple Create YouTube Dub can now inspect embedded subtitle streams in a selected NAS video, extract text subtitle tracks through the backend, refresh the NAS library, and select the extracted subtitle for the job."
                ),
                AppChangelogEntry(
                    id: "apple-create-ipad-two-column-detail",
                    title: "Create uses iPad space",
                    detail: "iPad and local Mac Designed for iPad Create now use a two-column detail editor, keeping source/setup fields on the left and narration, output, status, and submit settings on the right."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-23",
            dateLabel: "June 23, 2026",
            version: "2026.06.23.96",
            entries: [
                AppChangelogEntry(
                    id: "apple-create-ipad-detail-settings",
                    title: "Create settings moved right",
                    detail: "On iPad and local Mac Designed for iPad, Apple Create now keeps the job type and creation settings in the detail panel instead of spending sidebar space on job settings."
                ),
                AppChangelogEntry(
                    id: "apple-create-generated-book-history-defaults",
                    title: "Create remembers generated books",
                    detail: "Apple Create generated-book mode now reuses recent generated-book prompt, language, voice, narration, output, lookup, and image defaults without borrowing Narrate EPUB history."
                ),
                AppChangelogEntry(
                    id: "apple-create-subtitle-video-history-defaults",
                    title: "Create reuses job defaults",
                    detail: "Apple Create now mirrors Web rerun behavior for untouched subtitle and YouTube dubbing jobs by reusing recent sources, time offsets, translation settings, and video tuning defaults."
                ),
                AppChangelogEntry(
                    id: "apple-create-subtitle-show-original-memory",
                    title: "Create remembers subtitles",
                    detail: "Apple Create subtitle jobs now remember the Show Original preference per API/user scope, matching Web's returning-user subtitle default."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-base-dir",
                    title: "Create browses video roots",
                    detail: "Apple Create YouTube dubbing now exposes and remembers the NAS base directory, matching Web's alternate video-root refresh flow."
                ),
                AppChangelogEntry(
                    id: "apple-create-shared-language-defaults",
                    title: "Create remembers languages",
                    detail: "Apple Create now remembers shared input language, target languages, and lookup-cache defaults per API/user scope across generated book, Narrate EPUB, subtitle, and video jobs."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-source-memory",
                    title: "Create remembers videos",
                    detail: "Apple Create now remembers the last YouTube dubbing NAS video and subtitle selection per API/user scope and restores it when those files are still available."
                ),
                AppChangelogEntry(
                    id: "apple-create-youtube-newest-playable",
                    title: "Create picks latest videos",
                    detail: "Apple Create YouTube dubbing now defaults to the newest NAS video with a playable subtitle track, matching Web's server-backed video ordering."
                ),
                AppChangelogEntry(
                    id: "apple-create-latest-subtitle-source",
                    title: "Create picks latest subtitles",
                    detail: "Apple Create subtitle jobs now decode source modification timestamps and default to the latest usable SRT/VTT source, matching Web source-selection behavior."
                ),
                AppChangelogEntry(
                    id: "apple-create-recent-job-defaults",
                    title: "Create remembers narration",
                    detail: "Apple Create now reuses recent book and narration job history for untouched Narrate EPUB defaults, including source paths, resume start sentence, languages, and lookup-cache preference."
                ),
                AppChangelogEntry(
                    id: "apple-create-epub-picker-tolerant",
                    title: "Create shows server EPUBs",
                    detail: "Apple Create Narrate EPUB now keeps backend-visible server EPUBs in the picker even when source entries arrive with older or incomplete file-type metadata."
                ),
                AppChangelogEntry(
                    id: "apple-create-newest-nas-ebook",
                    title: "Create picks latest EPUB",
                    detail: "Web and Apple Create now receive newest-first EPUB listings with file metadata, so Narrate EPUB defaults to the latest backend-visible NAS ebook when the source has not been edited."
                ),
                AppChangelogEntry(
                    id: "apple-create-voice-preview",
                    title: "Create previews voices",
                    detail: "Apple Create now loads the shared TTS voice inventory, adds language-matched voice choices for source and target narration, and previews selected voices through backend audio synthesis."
                ),
                AppChangelogEntry(
                    id: "apple-create-subtitle-video-source-pickers",
                    title: "Create finds video sources",
                    detail: "Apple Create now loads backend subtitle sources and NAS YouTube/video library entries, with pickers that prefill subtitle jobs and YouTube dubbing jobs without manual path entry."
                ),
                AppChangelogEntry(
                    id: "apple-local-macos-ipad-style",
                    title: "Local Mac build destination",
                    detail: "The Apple pipeline now includes a repeatable local macOS Designed for iPad/iPhone build target and a guarded command-line helper for unattended iPhone/iPad updates when explicitly confirmed."
                ),
                AppChangelogEntry(
                    id: "apple-create-server-ebook-picker",
                    title: "Create finds server EPUBs",
                    detail: "Apple Create Narrate EPUB now loads backend-visible EPUBs, offers a server EPUB picker, and auto-fills the preferred or first NAS EPUB when the source is still empty."
                ),
                AppChangelogEntry(
                    id: "create-cache-source-identity",
                    title: "Create cache isolation",
                    detail: "Web and Apple Create chapter loading now keeps runtime ingestion caches separate for same-named EPUBs in different folders, preventing stale chapter data from another source file."
                ),
                AppChangelogEntry(
                    id: "create-refined-cache-invalidation",
                    title: "Create chapter freshness",
                    detail: "Web and Apple Create chapter loading now invalidates cached refined sentences when the source EPUB changes, keeping chapter ranges fresh after file edits or replacements."
                ),
                AppChangelogEntry(
                    id: "create-content-index-cache",
                    title: "Create chapters load faster",
                    detail: "Web and Apple Create chapter loading now reuses a validated backend content-index cache, avoiding repeated EPUB section parsing when users reopen the chapter picker."
                ),
                AppChangelogEntry(
                    id: "apple-create-default-aliases",
                    title: "Create defaults aligned",
                    detail: "Apple Create now accepts the same backend default aliases as Web creation surfaces for translation providers and transliteration modes, including gtrans, googletranslate, ollama, and python-module."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-job-presentation",
                    title: "Subtitle Jobs presentation",
                    detail: "Web Subtitle Tool Jobs presentation now lives in a focused module with direct pipeline coverage for download-link resolution, metadata labels, retry summaries, and narrated-library move eligibility."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-job-utils",
                    title: "Subtitle Jobs helpers",
                    detail: "Web Subtitle Tool Jobs helpers now live in a focused module with direct pipeline coverage for retry summaries, generated subtitle files, missing-result selection, and newest-first ordering."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-metadata-utils",
                    title: "Subtitle metadata helpers",
                    detail: "Web Subtitle Tool TV metadata draft helpers now live in a focused module with direct pipeline coverage for record coercion, editable metadata copying, text cleanup, and episode-code formatting."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-source-utils",
                    title: "Subtitle source selection",
                    detail: "Web Subtitle Tool source selection now lives in a focused module with direct pipeline coverage for ASS avoidance, latest-source picking, and metadata source labels."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-submit-feedback-utils",
                    title: "Subtitle submit feedback",
                    detail: "Web Subtitle Tool submitted-job feedback formatting now lives in a focused module so user-visible creation summaries stay pinned independently from the page shell."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-language-defaults-utils",
                    title: "Subtitle language defaults",
                    detail: "Web Subtitle Tool backend language-default mapping now lives in a focused module so target-language options and default input language stay pinned outside the page shell."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-prefill-utils",
                    title: "Subtitle prefill utilities",
                    detail: "Web Subtitle Tool rerun and prefill mapping now lives in a focused module so existing-job recreation stays pinned independently from the page shell."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-submit-utils",
                    title: "Subtitle submit utilities",
                    detail: "Web Subtitle Tool submit and timecode normalization helpers now live in a focused module so creation payload tests target the Web-to-Apple parity contract directly."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-submit-hook",
                    title: "Subtitle submit flow",
                    detail: "Web Subtitle Tool submit orchestration now lives in a focused hook with coverage for backend request handoff, field normalization, success feedback, intake refresh, and failure cleanup."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-submit-status-hook",
                    title: "Subtitle submit refactor",
                    detail: "Web Subtitle Tool submit status now lives in a focused hook with coverage for queue-capacity rejection, request failures, and submit busy-state transitions."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-tab-state-hook",
                    title: "Subtitle tab refactor",
                    detail: "Web Subtitle Tool tab state and newest-first job sorting now live in a focused hook with coverage for tab changes and Jobs panel ordering."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-processing-options-hook",
                    title: "Subtitle options refactor",
                    detail: "Web Subtitle Tool processing options now live in a focused hook with coverage for form defaults and prefill or normalization setters."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-source-mode-hook",
                    title: "Subtitle source refactor",
                    detail: "Web Subtitle Tool source mode and upload-file state now live in a focused hook with coverage for ASS-source detection, upload labels, and stale error clearing."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-submit-feedback-hook",
                    title: "Subtitle feedback refactor",
                    detail: "Web Subtitle Tool submit feedback now lives in a focused hook with coverage for submitted summary formatting and empty optional details."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-language-state-hook",
                    title: "Subtitle language refactor",
                    detail: "Web Subtitle Tool language state now lives in a focused hook with coverage for shared preferences, backend target-language options, and normalized input and target handlers."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-prefill-hook",
                    title: "Subtitle prefill refactor",
                    detail: "Web Subtitle Tool rerun and prefill application now lives in a focused hook with coverage for full, partial, absent, and updated parameter snapshots."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-show-original-hook",
                    title: "Subtitle preference refactor",
                    detail: "Web Subtitle Tool show-original subtitle preference now lives in a focused hook with coverage for stored values, persistence, and storage failures."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-language-defaults-hook",
                    title: "Subtitle defaults refactor",
                    detail: "Web Subtitle Tool backend language-default loading now lives in a focused hook with coverage for target lists, default input language, failed fetches, and stale responses."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-models-hook",
                    title: "Subtitle model refactor",
                    detail: "Web Subtitle Tool model-option loading now lives in a focused hook with coverage for success, empty, failed, and late-response flows."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-results-hook",
                    title: "Subtitle result refactor",
                    detail: "Web Subtitle Tool completed-result fetching now lives in a focused hook with coverage for dedupe, partial failures, and late-response cancellation."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-sources-hook",
                    title: "Subtitle source refactor",
                    detail: "Web Subtitle Tool source listing, selection preservation, refresh, and delete state now live in a focused hook with coverage for empty, failed, cancelled, and confirmed flows."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-metadata-hook",
                    title: "Subtitle metadata refactor",
                    detail: "Web Subtitle Tool TV metadata lookup state now lives in a focused hook with stale-request and draft-edit coverage, preserving the existing metadata workflow."
                ),
                AppChangelogEntry(
                    id: "web-create-intake-shared-callout",
                    title: "Web intake parity",
                    detail: "Web Subtitle Tool and Video Dubbing now reuse the Create job-intake status callout and disable new submissions when the backend queue is at capacity."
                ),
                AppChangelogEntry(
                    id: "create-intake-limit-details",
                    title: "Create queue limits",
                    detail: "Web and Apple Create now show delayed job count plus soft and hard queue limits in the job intake status."
                ),
                AppChangelogEntry(
                    id: "create-intake-loading-state",
                    title: "Create intake loading",
                    detail: "Web and Apple Create now show a visible Checking job intake state while the queue snapshot is loading."
                ),
                AppChangelogEntry(
                    id: "web-create-intake-refresh-success",
                    title: "Create refresh accuracy",
                    detail: "Web Create now refreshes backend job intake status only after a successful enqueue, matching the Apple Create behavior and avoiding misleading refreshes after rejected submissions."
                ),
                AppChangelogEntry(
                    id: "create-intake-status-refresh",
                    title: "Create queue refresh",
                    detail: "Web and Apple Create now refresh backend job intake status after successful submission, keeping queue pressure counts current after enqueue."
                ),
                AppChangelogEntry(
                    id: "create-intake-status",
                    title: "Create checks intake",
                    detail: "Web and Apple Create now show backend job intake status before submission, warning under queue pressure and blocking submit when the backend is at capacity."
                ),
                AppChangelogEntry(
                    id: "web-backend-queue-pressure",
                    title: "Queue pressure status",
                    detail: "Web admin System status now shows backend job intake pressure, pending depth, and running jobs before long job submissions."
                ),
                AppChangelogEntry(
                    id: "apple-web-create-handoff",
                    title: "Web create handoff",
                    detail: "Apple Create on iPhone and iPad now includes an Open Web Create action that deep-links to the matching advanced Web creation surface."
                ),
                AppChangelogEntry(
                    id: "apple-book-default-target-languages",
                    title: "Apple target defaults",
                    detail: "Apple generated-book and Narrate EPUB creation now preserve multi-target backend defaults in the visible Additional target languages field."
                ),
                AppChangelogEntry(
                    id: "web-book-default-target-languages",
                    title: "Web target defaults",
                    detail: "Web book narration now preserves multi-target defaults from persisted preferences, backend defaults, and latest-job settings in the visible Additional target languages field."
                ),
                AppChangelogEntry(
                    id: "web-book-prefill-target-languages",
                    title: "Web multi-target reuse",
                    detail: "Web book narration rerun and prefill now preserve additional target languages instead of collapsing multi-target history back to a single target."
                ),
                AppChangelogEntry(
                    id: "web-book-additional-target-languages",
                    title: "Web multi-target books",
                    detail: "Web book narration now exposes additional target languages and submits selected plus manual targets as a de-duplicated multi-target list, matching Apple Create behavior."
                ),
                AppChangelogEntry(
                    id: "apple-per-language-voice-overrides",
                    title: "Target voice overrides",
                    detail: "Apple generated-book and Narrate EPUB creation now expose per-target-language voice override pickers, matching the Web voice override payload shape while preserving the global target voice fallback."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-offset-keyboard",
                    title: "Narrate EPUB offsets",
                    detail: "Apple Narrate EPUB end-sentence entry now uses punctuation-capable input on iPhone and iPad, making Web-aligned +offset windows practical from the software keyboard."
                ),
                AppChangelogEntry(
                    id: "apple-create-audio-duration-estimate",
                    title: "Apple duration estimate",
                    detail: "Apple generated-book and Narrate EPUB creation now show Web-aligned estimated audio duration, and Narrate EPUB accepts +offset end-sentence windows before submit."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-ebook-chapter-ranges",
                    title: "Narrate EPUB chapter ranges",
                    detail: "Apple Narrate EPUB chapter selection now supports a consecutive start-to-end chapter range, matching the Web processing-window behavior."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-ebook-chapters",
                    title: "Narrate EPUB chapters",
                    detail: "Apple Narrate EPUB creation can now load a server EPUB chapter index and apply a selected chapter range to the submitted sentence window."
                ),
                AppChangelogEntry(
                    id: "apple-base-output-slugs",
                    title: "Apple output slugs",
                    detail: "Apple Create now derives Web-aligned output slugs from source filenames, stripping final file extensions from EPUB, subtitle, and video paths before submission."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-ebook-metadata",
                    title: "Narrate EPUB metadata",
                    detail: "Apple Narrate EPUB creation now exposes optional title, author, and genre metadata fields and submits them through Web-aligned book metadata and config aliases."
                ),
                AppChangelogEntry(
                    id: "apple-web-book-genres",
                    title: "Book genre lists",
                    detail: "Web and Apple book creation now submit structured book_genres arrays alongside visible book_genre text, keeping edited and lookup genres aligned across surfaces."
                ),
                AppChangelogEntry(
                    id: "active-book-request-aliases",
                    title: "Active request metadata",
                    detail: "In-memory book lookup enrichment now keeps book_isbn, book_genre, and book_genres aligned in active pipeline request config after metadata persistence."
                ),
                AppChangelogEntry(
                    id: "persisted-book-lookup-aliases",
                    title: "Persisted book metadata",
                    detail: "Persisted book lookup metadata now keeps book_isbn, book_genre, and book_genres in job media metadata and config after lookup enrichment."
                ),
                AppChangelogEntry(
                    id: "backend-book-lookup-aliases",
                    title: "Book lookup aliases",
                    detail: "Backend book lookup payloads now emit book_isbn, book_genre, and book_genres aliases directly across OpenLibrary, Google Books fallback, and unified metadata results."
                ),
                AppChangelogEntry(
                    id: "google-books-language-genre",
                    title: "Google Books metadata",
                    detail: "Google Books fallback metadata now preserves language, book_language, and genre aliases so creation forms receive the same enriched lookup shape when OpenLibrary falls through."
                ),
                AppChangelogEntry(
                    id: "book-language-metadata",
                    title: "Book language metadata",
                    detail: "Web and Apple book creation now preserve book_language in metadata and config payloads, and OpenLibrary lookup can carry source language hints into Web submissions."
                ),
                AppChangelogEntry(
                    id: "web-book-lookup-genre",
                    title: "Web lookup genre",
                    detail: "Web book metadata lookup now persists preview genres into book_genre, so submitted config overrides carry the selected lookup genre without manual editing."
                ),
                AppChangelogEntry(
                    id: "web-book-genre-isbn-config",
                    title: "Web metadata parity",
                    detail: "Web book narration now promotes edited genre and ISBN metadata into config overrides, matching the Apple book_genre and book_isbn payload shape."
                ),
                AppChangelogEntry(
                    id: "apple-book-isbn-metadata",
                    title: "Apple ISBN metadata",
                    detail: "Generated-book and Narrate EPUB metadata now expose ISBN and submit Web-aligned book_genre and book_isbn aliases."
                ),
                AppChangelogEntry(
                    id: "apple-web-shape-voice-overrides",
                    title: "Apple voice payloads",
                    detail: "Generated-book and Narrate EPUB voice overrides now mirror the Web payload shape in both pipeline inputs and pipeline overrides."
                ),
                AppChangelogEntry(
                    id: "apple-multi-target-voice-overrides",
                    title: "Apple target voices",
                    detail: "Generated-book and Narrate EPUB target voice overrides now apply across every submitted target language."
                ),
                AppChangelogEntry(
                    id: "apple-multi-target-books",
                    title: "Apple multi-target books",
                    detail: "Generated-book and Narrate EPUB creation now expose Web-aligned additional target languages and submit multi-target pipeline arrays."
                ),
                AppChangelogEntry(
                    id: "apple-image-api-url-overrides",
                    title: "Apple image API URLs",
                    detail: "Generated-book creation now exposes Web-aligned image API URL overrides for selecting home Draw Things and image worker nodes."
                ),
                AppChangelogEntry(
                    id: "apple-book-performance-overrides",
                    title: "Apple book performance",
                    detail: "Generated-book and Narrate EPUB creation now expose Web-aligned worker threads, queue size, and max job worker overrides for backend performance tuning."
                ),
                AppChangelogEntry(
                    id: "apple-book-cover-file",
                    title: "Apple book cover path",
                    detail: "Generated-book and Narrate EPUB creation now expose a Web-aligned cover file path field, submitting book_cover_file through metadata and config."
                ),
                AppChangelogEntry(
                    id: "apple-book-metadata-fields",
                    title: "Apple book metadata",
                    detail: "Generated-book and Narrate EPUB creation now expose Web-aligned metadata summary and year fields, submitting them through book_metadata and matching book config keys."
                ),
                AppChangelogEntry(
                    id: "apple-book-llm-model-picker",
                    title: "Apple book LLM model",
                    detail: "Generated-book and Narrate EPUB creation now expose the Web-aligned optional LLM model picker and submit ollama_model when selected."
                ),
                AppChangelogEntry(
                    id: "apple-target-voice-overrides",
                    title: "Apple target voice overrides",
                    detail: "Generated-book and Narrate EPUB creation now expose a target-language voice override that submits the backend voice_overrides payload when selected."
                ),
                AppChangelogEntry(
                    id: "apple-book-output-chunking",
                    title: "Apple output chunking",
                    detail: "Generated-book and Narrate EPUB creation now expose Web-aligned sentences-per-file and stitch-full-book output controls before submit."
                ),
                AppChangelogEntry(
                    id: "apple-book-translation-tuning",
                    title: "Apple translation tuning",
                    detail: "Generated-book and Narrate EPUB creation now expose Web-aligned translation provider, translation batch, transliteration mode/model, and lookup cache batch controls before submit."
                ),
                AppChangelogEntry(
                    id: "apple-narrate-sentence-range",
                    title: "Apple Narrate EPUB ranges",
                    detail: "Narrate EPUB creation on iPhone and iPad now exposes Web-aligned start and end sentence range controls before submit."
                ),
                AppChangelogEntry(
                    id: "apple-create-narration-controls",
                    title: "Apple narration controls",
                    detail: "Generated-book and Narrate EPUB creation on iPhone and iPad now expose Web-aligned narration controls for audio generation, audio mode, audio quality, written mode, and tempo before submit."
                ),
                AppChangelogEntry(
                    id: "apple-create-html-pdf-output",
                    title: "Apple HTML and PDF outputs",
                    detail: "Generated-book and Narrate EPUB creation on iPhone and iPad now expose Web-aligned HTML and PDF output toggles before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-performance",
                    title: "Apple image performance",
                    detail: "Generated-book creation on iPhone and iPad now lets illustration jobs optionally set image worker concurrency and image API timeout before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-continuity",
                    title: "Apple image continuity",
                    detail: "Generated-book creation on iPhone and iPad now lets illustration jobs seed from the previous generated image and enable backend blank-image detection before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-tuning",
                    title: "Apple image tuning",
                    detail: "Generated-book creation on iPhone and iPad now lets illustration jobs optionally set image steps, CFG scale, and sampler name before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-batching",
                    title: "Apple image batching",
                    detail: "Generated-book creation on iPhone and iPad now lets Prompt plan illustration jobs group sentences into shared images and tune prompt-plan batch size before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-dimensions",
                    title: "Apple image dimensions",
                    detail: "Generated-book creation on iPhone and iPad now lets Illustrations jobs set backend image width and height before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-prompt-pipeline",
                    title: "Apple image prompt pipeline",
                    detail: "Generated-book creation on iPhone and iPad now lets Illustrations jobs choose Prompt plan or Visual canon before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-prompt-context",
                    title: "Apple image prompt context",
                    detail: "Generated-book creation on iPhone and iPad now lets Illustrations jobs tune the backend image prompt context count before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-image-style",
                    title: "Apple illustration styles",
                    detail: "Generated-book creation on iPhone and iPad now lets Illustrations jobs choose the backend image style template before submit."
                ),
                AppChangelogEntry(
                    id: "apple-generated-book-illustrations-toggle",
                    title: "Apple generated-book illustrations",
                    detail: "Generated-book creation on iPhone and iPad now includes an Illustrations toggle that follows backend defaults and submits add_images with the job payload."
                ),
                AppChangelogEntry(
                    id: "backend-search-match-summary",
                    title: "Search backend allocation trimmed",
                    detail: "Generated-media search now keeps the first match span and occurrence count without building a large tuple list for repeated common terms, preserving Web and Apple search results."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-source-refresh-selection",
                    title: "Web Subtitle source selection fixed",
                    detail: "Subtitle Tool refresh now uses a tested source-selection rule that clears stale selections after deletes and chooses the latest usable subtitle source when needed."
                ),
                AppChangelogEntry(
                    id: "pipeline-subtitle-tool-web-check",
                    title: "Subtitle Tool Web check added",
                    detail: "The shared pipeline now runs the Subtitle Tool focused Web check for ebook-tools alongside Create, Library, Video Dubbing, and production/export build checks."
                ),
                AppChangelogEntry(
                    id: "web-video-dubbing-delete-selection",
                    title: "Web Video Dubbing selection hardened",
                    detail: "Deleting a NAS or YouTube video now uses a tested fallback that keeps the current selection when possible and chooses the next default subtitle when needed."
                ),
                AppChangelogEntry(
                    id: "pipeline-video-dubbing-web-check",
                    title: "Video Dubbing Web check added",
                    detail: "The shared pipeline now runs the Video Dubbing focused Web check for ebook-tools alongside Create, Library, and production/export build checks."
                ),
                AppChangelogEntry(
                    id: "web-library-metadata-update-plan",
                    title: "Web Library metadata saves hardened",
                    detail: "Library metadata edits now use a tested update plan that preserves source upload ordering, changed-ISBN apply behavior, and explicit ISBN clears."
                ),
                AppChangelogEntry(
                    id: "pipeline-web-library-check-redaction",
                    title: "Pipeline Web check hygiene",
                    detail: "The shared pipeline now runs a Library-focused Web check for ebook-tools and collapses Vite environment debug dumps while keeping generated build artifacts cleaned up."
                ),
                AppChangelogEntry(
                    id: "apple-job-creation-summary",
                    title: "Creation summaries in Jobs",
                    detail: "Job rows on iPhone, iPad, and Apple TV now surface generated-book creation messages, warnings, sample sentences, or seed EPUB context from backend metadata."
                )
            ]
        ),
        AppChangelogDay(
            id: "2026-06-22",
            dateLabel: "June 22, 2026",
            version: "2026.06.22.170",
            entries: june22Entries
        ),
        AppChangelogDay(
            id: "2026-06-21",
            dateLabel: "June 21, 2026",
            version: "2026.06.21.11",
            entries: [
                AppChangelogEntry(
                    id: "root-lifecycle-modifiers",
                    title: "Root lifecycle cleaned up",
                    detail: "Notification registration, keyboard shortcuts, session restore, and offline sync now live in focused SwiftUI modifiers for safer cross-device iteration."
                ),
                AppChangelogEntry(
                    id: "explicit-version-badge-frame",
                    title: "Version badge frame hardened",
                    detail: "Version badges now render inside an explicit fixed-size shape so cramped iPad headers cannot reflow the release text into vertical characters."
                ),
                AppChangelogEntry(
                    id: "settings-section-refactor",
                    title: "Settings review surface cleaned up",
                    detail: "Connection, playback, changelog, voice, and notification settings now render through focused section components for safer iPad and tvOS iteration."
                ),
                AppChangelogEntry(
                    id: "wd-staging-pipeline-contract",
                    title: "WD staging pipeline aligned",
                    detail: "ebook-tools and Finance Review now share the same Mac Studio WD staging convention before backend maintenance."
                ),
                AppChangelogEntry(
                    id: "compact-version-build-token",
                    title: "iPad version chip fixed",
                    detail: "Compact browse headers now show the short daily build token while full release metadata remains visible in roomy surfaces."
                ),
                AppChangelogEntry(
                    id: "compact-version-chip-width",
                    title: "Compact version chip width",
                    detail: "Compact headers now use a shorter fixed-width chip with fixed-size monospaced text so the release cannot stack vertically in split view."
                ),
                AppChangelogEntry(
                    id: "version-layout-defensive-rows",
                    title: "Version layout hardened",
                    detail: "Version text now owns its ideal width before the pill is drawn, and changelog headers no longer squeeze full version labels beside the date."
                ),
                AppChangelogEntry(
                    id: "version-pill-owns-width",
                    title: "Version badge no longer squeezes",
                    detail: "The login badge now owns a full row and toolbar headers use a compact daily label so iPad cannot stack the version vertically."
                ),
                AppChangelogEntry(
                    id: "ipad-version-pill-layout",
                    title: "iPad version badge layout",
                    detail: "The release pill now stays on one line in crowded iPad headers instead of collapsing into vertical characters."
                ),
                AppChangelogEntry(
                    id: "apple-bundle-versioning",
                    title: "Device inventory versioning",
                    detail: "Installed device metadata now carries the daily build number so CoreDevice checks can identify the deployed app."
                ),
                AppChangelogEntry(
                    id: "release-contract-guard",
                    title: "Daily release contract guard",
                    detail: "A repo check now keeps Info plists, in-app changelog, Markdown changelog, and journey badge assertions in sync."
                ),
                AppChangelogEntry(
                    id: "backend-runtime-settings",
                    title: "Backend runtime visible in Settings",
                    detail: "Settings now verifies the public ebook-tools API descriptor and shows the service/version without exposing tokens."
                ),
                AppChangelogEntry(
                    id: "pipeline-backend-preflight",
                    title: "Pipeline backend preflight",
                    detail: "Simulator smoke profiles now fail fast on backend health and runtime identity before Xcode builds."
                ),
                AppChangelogEntry(
                    id: "settings-connection-keychain",
                    title: "Connection and Keychain state",
                    detail: "Settings shows API host, signed-in session, and Keychain token storage for attended device review."
                ),
                AppChangelogEntry(
                    id: "apple-tv-icon-remote",
                    title: "tvOS deployment polish",
                    detail: "Apple TV icon assets and remote-driven playback journeys are covered by the shared pipeline."
                )
            ]
        )
    ]
}
