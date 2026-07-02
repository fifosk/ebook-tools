extension AppChangelogData {
    static let june30Entries: [AppChangelogEntry] = [
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
}
