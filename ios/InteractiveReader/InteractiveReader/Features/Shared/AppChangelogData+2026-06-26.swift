extension AppChangelogData {
    static let june26Entries: [AppChangelogEntry] = [
                AppChangelogEntry(
                    id: "ipad-read-aloud-keeps-arrow-navigation",
                    title: "Read Aloud keeps arrow keys",
                    detail: "iPad lookup Read Aloud now reclaims the shared player keyboard path after pronunciation audio or fallback speech starts, finishes, or cancels, and duplicate bubble-local arrow shortcuts were removed so Left and Right keep moving lookup words."
                ),
                AppChangelogEntry(
                    id: "ipad-video-lookup-keyboard-single-path",
                    title: "Video lookup keys match books",
                    detail: "iPad video playback now uses the same shared player keyboard path after lookup Read Aloud starts and no longer registers duplicate hidden SwiftUI arrow shortcuts over the video subtitle bubble."
                ),
                AppChangelogEntry(
                    id: "ipad-lookup-bubble-arrows-own-transport",
                    title: "Lookup bubble owns arrow keys",
                    detail: "When an iPad lookup bubble is open, plain Left and Right now navigate lookup words before playback transport checks run, avoiding stale AVPlayer playing-state from stealing paused word navigation."
                ),
                AppChangelogEntry(
                    id: "apple-create-acquisition-contract-readiness",
                    title: "Create discovery routes are guarded",
                    detail: "Apple Settings and Create readiness now surface acquisition provider, discover, acquire, job, artifact-prepare, and template route contracts so iPhone, iPad, Apple TV, and Web creation handoffs stay aligned."
                ),
                AppChangelogEntry(
                    id: "ipad-bubble-arrow-repeat-stability",
                    title: "iPad lookup arrows keep repeating",
                    detail: "Paused iPad lookup-bubble Left and Right keys now route each word move through a single definition refresh, avoiding duplicate lookup state churn after the first arrow press."
                ),
                AppChangelogEntry(
                    id: "reader-gate-only-dutch-sync",
                    title: "Translation-only chunks hold sync",
                    detail: "Interactive Reader now trusts sentence gate boundaries even when a job has no per-word timing tokens, keeping Dutch-only playback, slider jumps, and rendered sentences aligned around chunk edges."
                ),
                AppChangelogEntry(
                    id: "apple-create-preference-scope",
                    title: "Create preferences are scoped cleaner",
                    detail: "Apple Create now routes YouTube base directory, remembered source selections, subtitle original-display, language defaults, and YouTube library cache keys through one API/user-scoped preference wrapper."
                ),
                AppChangelogEntry(
                    id: "reader-language-sync-keyboard-hardening",
                    title: "Reader sync fixes tightened",
                    detail: "Apple playback now accepts generated-book target languages from book metadata, avoids source-language destination pills, keeps translation-only timing on the active audio lane, and refreshes paused lookup definitions from every arrow-key word navigation path."
                ),
                AppChangelogEntry(
                    id: "apple-youtube-template-application-helper",
                    title: "YouTube templates apply cleaner",
                    detail: "Apple Create now resolves saved YouTube Dub template source, language, timing, model, tuning, output, and lookup settings through the shared template settings helper before applying them to the native form."
                ),
                AppChangelogEntry(
                    id: "reader-target-language-authoritative-fields",
                    title: "Destination pills avoid stale metadata",
                    detail: "Interactive Reader now resolves destination language pills from authoritative job target fields and known request/config containers instead of broad nested metadata scans that could surface an unrelated book language."
                ),
                AppChangelogEntry(
                    id: "reader-single-track-combined-sync",
                    title: "Translation-only playback stays aligned",
                    detail: "When Original is disabled on a combined-track book, Apple playback now treats the active audio role and timing as translation-only so the header, slider, rendered sentence, and narration stay together."
                ),
                AppChangelogEntry(
                    id: "ipad-paused-bubble-selection-lookup",
                    title: "Paused lookup arrows refresh directly",
                    detail: "Paused iPad lookup-bubble Left and Right keys now refresh definitions from the newly selected word directly, even when the bubble's local keyboard shortcut path handles the arrow event."
                ),
                AppChangelogEntry(
                    id: "reader-playback-language-sync-hardening",
                    title: "Reader track sync is tighter",
                    detail: "Interactive Reader now prefers target_languages metadata for destination pills, ignores stale selected audio tracks when Original or Translation is disabled, and refreshes paused lookup definitions from the exact word moved to by iPad arrow keys."
                ),
                AppChangelogEntry(
                    id: "reader-target-language-pill-source-fix",
                    title: "Reader language pills stay honest",
                    detail: "Apple playback now treats book_language as source metadata only, so the destination pill comes from target or translation fields instead of showing the source language for newly generated jobs."
                ),
                AppChangelogEntry(
                    id: "reader-text-audio-track-sync",
                    title: "Track toggles keep audio aligned",
                    detail: "When Original or Translation text tracks are hidden, Apple playback now aligns the narration audio mode to the visible track and clears stale lookup selections that pointed at hidden text."
                ),
                AppChangelogEntry(
                    id: "ipad-lookup-arrow-definition-refresh",
                    title: "Lookup arrows update definitions",
                    detail: "Paused iPad lookup-bubble Left and Right keys now refresh the definition immediately after moving the highlighted word instead of waiting for the delayed auto-lookup timer."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-bubble-arrow-dispatch-refresh",
                    title: "Lookup arrows refresh words",
                    detail: "Paused iPad lookup-bubble Left and Right keys now route through the bubble word-navigation path across UIKit, SwiftUI, app-command, and hardware-keyboard fallback sources, so the highlighted word and lookup definition advance together."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-bubble-local-arrow-shortcuts",
                    title: "iPad bubble arrows are steadier",
                    detail: "The lookup bubble now owns local iPad Left and Right keyboard shortcuts too, so paused word navigation keeps working even when the bubble itself has hardware-keyboard focus."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-keyboard-fallback-mounted",
                    title: "iPad lookup arrows work",
                    detail: "Interactive Reader now mounts the SwiftUI hardware-keyboard fallback layer, so plain Left and Right move the highlighted lookup word while paused even after the lookup bubble or other controls shift focus."
                ),
                AppChangelogEntry(
                    id: "ipad-reader-keyboard-debug-breadcrumbs",
                    title: "iPad keyboard debugging is clearer",
                    detail: "DEBUG builds now record Interactive Reader shortcut dispatch and word-selection breadcrumbs, making future physical-iPad hardware-key regressions traceable from device logs."
                ),
                AppChangelogEntry(
                    id: "ipad-video-keyboard-fallback-layer",
                    title: "Video lookup keys match books",
                    detail: "iPad video playback now has its own hardware-keyboard fallback layer, keeping paused lookup bubble previous/next word navigation aligned with Interactive Reader."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-tab-content-component",
                    title: "Subtitle tabs render cleaner",
                    detail: "Web Subtitle Tool now routes source, options, tuning, metadata, and jobs tabs through a focused tab-content component with coverage that preserves the shared submit form for Apple parity work."
                ),
                AppChangelogEntry(
                    id: "video-footer-slider-stays-hidden",
                    title: "Video keeps one scrubber",
                    detail: "Video playback now keeps the shared footer slider out of the video surface and drops stale overlay scrubber bindings, leaving iPhone and iPad to the native player timeline."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-creation-defaults-hook",
                    title: "Subtitle defaults load cleaner",
                    detail: "Web Subtitle Tool now loads backend creation defaults through a focused hook with coverage for template/prefill skips, failures, and late responses before Apple parity checks reuse the form."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-template-save-hook",
                    title: "Subtitle templates save cleaner",
                    detail: "Web Subtitle Tool now saves reusable subtitle creation templates through a focused hook with coverage for validation, sanitized payloads, and save-error state before Apple Create reuse."
                ),
                AppChangelogEntry(
                    id: "web-subtitle-template-handoff-hook",
                    title: "Subtitle templates apply cleaner",
                    detail: "Web Subtitle Tool now applies saved creation-template handoffs through a focused hook with coverage for compatible templates, incompatible templates, and metadata draft replacement before Apple reuse."
                ),
                AppChangelogEntry(
                    id: "apple-template-selection-helper",
                    title: "Create templates select cleaner",
                    detail: "Apple Create now resolves saved-template picker display and refresh/delete fallback selection through the shared template helper, keeping native picker and Web handoff compatibility rules aligned."
                ),
                AppChangelogEntry(
                    id: "apple-web-handoff-template-filter",
                    title: "Web handoff keeps matching templates",
                    detail: "Apple Create now resolves the selected Web handoff template through the shared template helper, so stale ids from another Create mode are not added to Open Web Create links."
                ),
                AppChangelogEntry(
                    id: "apple-template-discovery-apply-helper",
                    title: "Templates restore discovery cleaner",
                    detail: "Apple Create now restores saved book discovery state through the shared template helper, keeping source-panel selection and catalog metadata extras aligned with Web templates."
                ),
                AppChangelogEntry(
                    id: "apple-download-station-completion-helper",
                    title: "Download handoff reconnects cleaner",
                    detail: "Apple Create now matches completed Download Station tasks back to refreshed manual-download videos through a shared helper that reads top-level completed files and older metadata hints."
                ),
                AppChangelogEntry(
                    id: "video-ios-native-scrubber-only",
                    title: "Video uses the native scrubber",
                    detail: "iPhone and iPad video playback now hides the custom overlay timeline pill when native AVPlayer controls are available, avoiding duplicate progress controls."
                ),
                AppChangelogEntry(
                    id: "create-api-backed-splitter-picker",
                    title: "Create uses backend splitter labels",
                    detail: "Web and Apple Create now build sentence-splitter pickers from the backend capability contract, with local fallbacks for older options payloads."
                ),
                AppChangelogEntry(
                    id: "create-readiness-splitter-capabilities",
                    title: "Create preflight checks splitters",
                    detail: "Apple Create readiness now validates the backend sentence splitter capability contract, including supported modes, cache versions, and no-skip comparison metric fields."
                ),
                AppChangelogEntry(
                    id: "create-options-splitter-capabilities",
                    title: "Create advertises splitter capabilities",
                    detail: "The shared Create options payload now includes supported sentence splitter modes, cache versions, and comparison metric keys so Web and Apple can dogfood splitter quality from the same backend contract."
                ),
                AppChangelogEntry(
                    id: "sentence-splitter-contiguous-coverage",
                    title: "Splitter checks skipped text",
                    detail: "Backend sentence-splitter dry runs now report contiguous source-span coverage, skipped text, and unmatched sentence counts so modern splitter trials can catch no-skip/no-overlap regressions before reader jobs are created."
                ),
                AppChangelogEntry(
                    id: "apple-auth-runtime-contract",
                    title: "Auth routes join preflight",
                    detail: "Apple Settings now validates login, OAuth, session, and token-transport runtime metadata, and Create readiness checks auth descriptor drift before simulator or device runs."
                ),
                AppChangelogEntry(
                    id: "tvos-video-native-scrubber-only",
                    title: "Video uses native scrubbing",
                    detail: "Video playback no longer draws custom footer or header progress controls over native Apple video transport, keeping remote focus on playback buttons, captions, bookmarks, and segment status."
                ),
                AppChangelogEntry(
                    id: "apple-playback-media-linguist-runtime-contract",
                    title: "Playback routes join preflight",
                    detail: "The public runtime descriptor now advertises Apple playback media, timing, lookup-cache, assistant lookup, and audio synthesis routes, and Settings validates them before simulator or device use."
                ),
                AppChangelogEntry(
                    id: "apple-pipeline-jobs-runtime-contract",
                    title: "Jobs routes join preflight",
                    detail: "The public runtime descriptor now advertises Apple Jobs list, status, live update, delete, and restart routes, and Settings validates them before simulator or device use."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-jumps-wait-for-transcript",
                    title: "Reader jumps keep text and audio together",
                    detail: "Interactive Reader sentence jumps now wait for renderable chunk metadata before preparing audio, so iPad and iPhone no longer keep the loading wheel visible while the jumped sentence is already playing."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-tv-slider-scrubs",
                    title: "TV slider scrubs sentences",
                    detail: "Apple TV Interactive Reader now consumes left and right remote presses while the footer progress slider is focused, moving the sentence slider instead of falling through to previous or next word highlighting."
                ),
                AppChangelogEntry(
                    id: "apple-create-template-metadata-sanitizer",
                    title: "Create templates stay token-free",
                    detail: "Apple Create now strips token, password, secret, authorization, and API-key metadata extras before they can be saved into Narrate EPUB or generated-book templates."
                ),
                AppChangelogEntry(
                    id: "apple-job-event-stream-route-helper",
                    title: "Job live updates share routes",
                    detail: "Apple job live-update streams now use the shared pipeline job runtime route helper and encoded job-id path contract instead of carrying an inline events URL."
                ),
                AppChangelogEntry(
                    id: "apple-create-immediate-epub-import",
                    title: "Create imports EPUBs sooner",
                    detail: "Apple Create now uploads a chosen local EPUB into the shared server EPUB folder immediately, refreshes the server picker, and submits Narrate EPUB jobs using the uploaded backend path."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-dense-token-taps",
                    title: "Dense text taps are steadier",
                    detail: "Interactive Reader now treats near-token taps on dense iPhone and iPad text as word taps, preserving seek and lookup behavior instead of letting those taps fall through as background playback toggles."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-tv-progress-focus",
                    title: "TV reader progress focus is explicit",
                    detail: "Apple TV Interactive Reader now has a dedicated progress focus area, so pressing down from the transcript can reach the sentence footer while Video keeps its existing native overlay scrubber focus path."
                ),
                AppChangelogEntry(
                    id: "iphone-reader-progress-footer-hide",
                    title: "iPhone reader progress gets out of the way",
                    detail: "Interactive Reader now keeps the full sentence slider hidden on iPhone until it is surfaced from a compact progress pill, reserves bottom transcript space while it is visible, keeps renderable tracks visible during slider jumps, and lets the slider be dismissed after seeking."
                ),
                AppChangelogEntry(
                    id: "tvos-video-single-scrubber",
                    title: "Video keeps one scrubber",
                    detail: "Video playback on Apple devices now uses the native player scrubber without also drawing the shared bottom footer, removing duplicate timeline controls."
                ),
                AppChangelogEntry(
                    id: "cross-surface-progress-footer",
                    title: "Progress stays handy",
                    detail: "Interactive Reader now keeps its thin sentence progress footer across iPhone, iPad, Apple TV, and Mac Designed for iPad, while video playback stays with the native scrubber."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-header-tightened",
                    title: "Reader header is tighter",
                    detail: "The Interactive Reader identity header now keeps title, author, category/type, and model metadata on one compact line where possible, with sentence scrubbing kept in the footer."
                ),
                AppChangelogEntry(
                    id: "now-playing-resume-existing",
                    title: "Now Playing returns in place",
                    detail: "Return to Now Playing now reopens the active book or job in a resume-only continue mode, so it resumes the rendered position when available instead of falling back to the beginning."
                ),
                AppChangelogEntry(
                    id: "apple-music-reading-bed-requested-playback",
                    title: "Apple Music follows narration",
                    detail: "Apple Music background beds now resume as soon as sentence playback is requested, covering startup and track-switch timing while still respecting manually paused music."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-overlay-pause-transition",
                    title: "TV return and pause are tighter",
                    detail: "Apple TV now shows a focused bottom Now Playing return overlay after backing out of playback, and interactive sentence track switches respect a pause made while the next track is loading."
                ),
                AppChangelogEntry(
                    id: "sentence-splitter-time-abbreviation-losslessness",
                    title: "Book sentence splitting is safer",
                    detail: "Backend book splitting now treats a.m. and p.m. as sentence endings only before clear new sentences, keeps lowercase continuations together, and invalidates refined caches with splitter version regex-v8."
                ),
                AppChangelogEntry(
                    id: "apple-runtime-preflight-playback-return",
                    title: "Preflight and playback return tighten",
                    detail: "Apple Create readiness now checks Library action, offline export, playback-state, and notification runtime contracts; Apple TV keeps Return to Now Playing in the browse list; Apple Music reading-bed sentence switches respect paused music."
                ),
                AppChangelogEntry(
                    id: "apple-offline-export-download-route-helper",
                    title: "Offline export route is ready",
                    detail: "Apple offline-export downloads now have a shared helper for the advertised runtime template, keeping future native download handling aligned with Settings and Create-readiness preflight."
                ),
                AppChangelogEntry(
                    id: "apple-create-route-template-helpers",
                    title: "Create routes align with preflight",
                    detail: "Saved-template detail routes and acquisition job polling now substitute the same Create runtime templates that Settings validates before Apple Create journeys run."
                ),
                AppChangelogEntry(
                    id: "apple-library-metadata-route-templates",
                    title: "Library metadata routes align",
                    detail: "Apple Library item edits, source uploads, ISBN apply, and metadata enrichment now substitute the same runtime route templates that Settings validates before simulator or device use."
                ),
                AppChangelogEntry(
                    id: "apple-library-media-file-route-helper",
                    title: "Library media routes share helpers",
                    detail: "Apple playback and offline sync now build and parse Library media file URLs through the shared media route contract, keeping encoded asset paths consistent across iPhone, iPad, Apple TV, and local Mac."
                ),
                AppChangelogEntry(
                    id: "apple-music-toggle-play-intent",
                    title: "Music toggle follows play intent",
                    detail: "Turning Background Music back on with Apple Music selected now uses the same play-requested guard as sentence switches, so paused readers stay quiet until narration resumes."
                ),
                AppChangelogEntry(
                    id: "apple-notification-runtime-contract",
                    title: "Notification routes join preflight",
                    detail: "Notification device registration, device removal, test notification, rich-test notification, and preference endpoints now appear in the public Apple runtime contract and use shared Apple route helpers."
                ),
                AppChangelogEntry(
                    id: "apple-auth-reading-bed-runtime-contract",
                    title: "Auth and reading-bed routes join preflight",
                    detail: "OAuth login and reading-bed catalog paths now appear in the public Apple runtime contract, and Apple auth, session, runtime descriptor, bookmark, resume, and reading-bed calls use shared route helpers for stronger drift checks."
                ),
                AppChangelogEntry(
                    id: "apple-media-linguist-route-contracts",
                    title: "Playback routes share helpers",
                    detail: "Apple playback media, timing, subtitle metadata, lookup-cache, assistant lookup, and audio synthesis endpoints now use shared route helpers so iPhone, iPad, Apple TV, and local Mac avoid inline API string drift."
                ),
                AppChangelogEntry(
                    id: "apple-job-library-action-runtime-contract",
                    title: "Job and Library actions join preflight",
                    detail: "Apple Jobs and Library move/remove endpoints now live in shared runtime contract helpers and the public backend descriptor, so Settings and readiness checks catch action route drift before simulator or device deployment."
                ),
                AppChangelogEntry(
                    id: "apple-runtime-descriptor-payload-check-full-create",
                    title: "Runtime payload check is stricter",
                    detail: "The standalone Swift runtime-descriptor payload check now mirrors the backend camelCase descriptor and decodes every advertised Create route, so descriptor additions stay covered by the shared Apple contract lane."
                ),
                AppChangelogEntry(
                    id: "apple-media-search-runtime-contract",
                    title: "Playback search contract shared",
                    detail: "The backend runtime descriptor now advertises the media-search endpoint used by Apple playback, and Apple Create readiness validates the full Create route contract before simulator journeys run."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-return-selector",
                    title: "TV Now Playing return is testable",
                    detail: "The Apple TV floating Now Playing dock now exposes the same Return to Now Playing automation target as the browse strip, keeping the Back/Menu return path visible and covered by unattended playback journeys."
                ),
                AppChangelogEntry(
                    id: "sentence-splitter-bullet-unicode-starts",
                    title: "Sentence splitting keeps more text",
                    detail: "Book sentence splitting now preserves leading bullet markers, recognizes Unicode lowercase starts after terminal punctuation, and invalidates refined sentence caches with splitter version regex-v7."
                ),
                AppChangelogEntry(
                    id: "apple-chapter-jumps-keep-play-intent",
                    title: "Chapter jumps keep playback intent",
                    detail: "Apple chapter menu and range-selector jumps now preserve requested playback during sentence transitions, matching Search, Bookmarks, and the header progress slider across iPhone, iPad, Apple TV, and local Mac."
                ),
                AppChangelogEntry(
                    id: "apple-music-disabled-source-stays-idle",
                    title: "Music stays idle when off",
                    detail: "Selecting Apple Music as the reading-bed source no longer claims playback mixing or Now Playing ownership while Background Music is off, keeping paused sentence switches quiet until music is enabled again."
                ),
                AppChangelogEntry(
                    id: "apple-music-external-pause-intent",
                    title: "Music respects external pauses",
                    detail: "Apple Music reading-bed playback now treats Control Center or lock-screen pauses as manual pause intent, so sentence switches do not restart music until the user resumes it."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-mini-return",
                    title: "TV gets a Now Playing mini control",
                    detail: "Apple TV now keeps a compact Now Playing return control floating in the browse shell after backing out of playback, while the existing return strip remains available for list-based journeys."
                ),
                AppChangelogEntry(
                    id: "apple-api-path-component-encoding",
                    title: "Apple routes encode IDs safely",
                    detail: "Apple playback, Library, media, lookup, event-stream, and notification calls now encode path components with route separators escaped, matching the safer Web and template handoff behavior."
                ),
                AppChangelogEntry(
                    id: "apple-now-playing-search-return",
                    title: "Search keeps Now Playing nearby",
                    detail: "The iPad and Mac-style Search surface now keeps the Return to Now Playing strip visible after leaving playback, so the active job or library item has a direct return action."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-menu-return",
                    title: "TV menu shows Now Playing",
                    detail: "Apple TV now shows the Return to Now Playing row at the top of the browse menu after backing out of playback, giving the remote a direct focused path back to the active item."
                ),
                AppChangelogEntry(
                    id: "apple-download-station-completed-file-message",
                    title: "Apple download completion names files",
                    detail: "Apple Create now names completed Download Station files from the same top-level and metadata fallback hints used by Web, so the handoff panel and status message agree."
                ),
                AppChangelogEntry(
                    id: "web-download-station-metadata-fallback",
                    title: "Web downloads use fallback hints",
                    detail: "Web Video Dubbing now reads Download Station completed-file hints from acquisition job metadata, matching the Apple fallback path when top-level status fields are missing."
                ),
                AppChangelogEntry(
                    id: "download-station-completed-file-metadata",
                    title: "Downloads reconnect consistently",
                    detail: "Completed Download Station file hints now appear in acquisition job metadata as well as status fields, giving Web and Apple Create the same fallback path for finished downloads."
                ),
                AppChangelogEntry(
                    id: "apple-music-auto-resume-play-intent",
                    title: "Music follows play intent",
                    detail: "Apple Music used as the reading bed now auto-resumes only when narration playback is still requested and active, so paused jumps and sentence switches do not restart music unexpectedly."
                ),
                AppChangelogEntry(
                    id: "apple-download-station-job-metadata-hints",
                    title: "Downloads reconnect more reliably",
                    detail: "Apple Create now preserves Download Station job metadata and uses safe completed-file hints as a fallback when matching finished downloads back to manual video discovery."
                ),
                AppChangelogEntry(
                    id: "apple-create-readiness-discovery-route",
                    title: "Create checks discovery search",
                    detail: "Apple Create readiness now makes bounded book and video discovery calls against backend-owned default providers, validating response shape before simulator or device journeys start."
                ),
                AppChangelogEntry(
                    id: "tvos-now-playing-return-overlay",
                    title: "TV can return to Now Playing",
                    detail: "Apple TV now keeps a floating Now Playing return control in the browse shell after backing out of playback, giving the current job or library item a direct re-entry point."
                ),
                AppChangelogEntry(
                    id: "apple-create-readiness-acquisition-defaults",
                    title: "Create checks discovery defaults",
                    detail: "Apple Create readiness now validates backend-owned book and video acquisition default provider ids before simulator or device journeys start."
                ),
                AppChangelogEntry(
                    id: "web-narrate-discovery-provider-helper",
                    title: "Discovery provider checks are focused",
                    detail: "Web Narrate Ebook discovery-provider ordering, availability messages, and backend default selection now live in a focused helper covered by the shared Create-intake pipeline gate."
                ),
                AppChangelogEntry(
                    id: "acquisition-provider-default-selection",
                    title: "Discovery defaults drive Create",
                    detail: "Web and Apple Create now adopt backend-owned default book and video discovery providers for the initial picker choice while keeping any provider the user selects manually."
                ),
                AppChangelogEntry(
                    id: "acquisition-provider-defaults",
                    title: "Discovery defaults are shared",
                    detail: "The acquisition provider API now advertises backend-owned default book and video discovery providers so Web and Apple Create can stay aligned with server behavior."
                ),
                AppChangelogEntry(
                    id: "acquisition-provider-discovery-media-kinds",
                    title: "Discovery providers are clearer",
                    detail: "The backend now marks which acquisition providers support book or video discovery, and Web plus Apple Create prefer that shared contract before falling back to older capability hints."
                ),
                AppChangelogEntry(
                    id: "apple-now-playing-return-command",
                    title: "Now Playing return is clearer",
                    detail: "Apple browse surfaces now label the Now Playing control as a return action and use an action-oriented symbol so the path back to active playback is easier to spot."
                ),
                AppChangelogEntry(
                    id: "apple-pause-safe-sequence-transitions",
                    title: "Paused playback stays paused",
                    detail: "Apple sentence-sequence transitions now respect the current pause intent across dwell, track switches, and direct jumps, keeping narration and Apple Music from restarting unexpectedly."
                ),
                AppChangelogEntry(
                    id: "apple-now-playing-return-focus",
                    title: "Now Playing stays reachable",
                    detail: "Apple browse surfaces now remember the active playback target and refocus the Now Playing return control on Apple TV after backing out of playback."
                ),
                AppChangelogEntry(
                    id: "apple-resume-menu-freshest-entry",
                    title: "Resume actions match the badge",
                    detail: "Apple Library, Jobs, and search menus now choose the freshest local or cloud resume point, matching the resume badge shown on the row."
                ),
                AppChangelogEntry(
                    id: "apple-create-shared-draft-submit",
                    title: "Create drafts stay consistent",
                    detail: "Apple Create submission and template saving now use the same current draft builders for generated books, Narrate EPUB, subtitles, and YouTube Dub jobs, including video discovery metadata."
                ),
                AppChangelogEntry(
                    id: "apple-cross-surface-now-playing-return",
                    title: "Now Playing return is cross-surface",
                    detail: "The browse shell now shows a Now Playing return strip on compact iPhone/iPad, Mac-style, and Apple TV surfaces when playback is active and you navigate away."
                ),
                AppChangelogEntry(
                    id: "apple-create-settings-content-refactor",
                    title: "Create settings are easier to evolve",
                    detail: "Apple Create now keeps mode-specific settings section ordering in a dedicated SwiftUI view, making the shared iPhone, iPad, Mac-style, and TV creation surface safer to keep aligned."
                ),
                AppChangelogEntry(
                    id: "cross-surface-manifest-gate",
                    title: "Checkpoint mirrors shared manifest",
                    detail: "The repo-owned cross-surface checkpoint now runs the full shared backend slice set, focused Web checks, full Vitest, Web builds, and Apple local-surface verification before safe checkpoints."
                ),
                AppChangelogEntry(
                    id: "cross-surface-library-playback-gate",
                    title: "Checkpoint covers playback surfaces",
                    detail: "The repo-owned cross-surface checkpoint now includes Library, playback, Sidebar, Job Progress, and app-view checks alongside Create, video, subtitle, Web build, and Apple local-surface verification."
                ),
                AppChangelogEntry(
                    id: "cross-surface-subtitle-video-gate",
                    title: "Checkpoint covers video and subtitles",
                    detail: "The repo-owned cross-surface checkpoint now covers backend subtitle and YouTube dubbing slices plus focused Web Video Dubbing and Subtitle Tool tests before Web builds and Apple local-surface verification."
                ),
                AppChangelogEntry(
                    id: "apple-music-pause-now-playing-return",
                    title: "Music pause and TV return improve",
                    detail: "Apple Music used as the reading bed now respects a manual pause across sentence transitions, and Apple TV shows a Now Playing return control above the browse menu for the current job or library item."
                ),
                AppChangelogEntry(
                    id: "apple-deploy-stable-artifact-guard",
                    title: "Device deploys handle stale artifacts",
                    detail: "Unattended Apple deploys now verify stable signed artifacts before CoreDevice preflight or install, and locked-device launch denials after a verified install are reported without failing the deploy."
                ),
                AppChangelogEntry(
                    id: "cross-surface-backend-create-gate",
                    title: "Cross-surface gate covers backend Create",
                    detail: "The repo-owned cross-surface checkpoint now runs backend creation-template and acquisition route tests before the Web Create checks, Web build, and Apple local-surface verification."
                ),
                AppChangelogEntry(
                    id: "cross-surface-web-create-gate",
                    title: "Cross-surface gate covers Web Create",
                    detail: "The repo-owned cross-surface checkpoint now runs focused Web Create intake and saved-template tests before the Web build and Apple local-surface verification."
                ),
                AppChangelogEntry(
                    id: "web-narrate-discovery-template-tab",
                    title: "Web discovery templates reopen clearly",
                    detail: "Web Narrate Ebook now switches back to the Discovery source tab when a saved discovery-backed template is applied, so the visible source mode matches the preserved provenance."
                ),
                AppChangelogEntry(
                    id: "web-narrate-template-discovery-resave",
                    title: "Web templates keep discovery context",
                    detail: "Web Narrate Ebook now preserves sanitized discovery source provenance when a saved discovery-backed template is applied and saved again."
                ),
                AppChangelogEntry(
                    id: "apple-create-discovery-template-panel",
                    title: "Discovery templates reopen cleanly",
                    detail: "Apple Narrate EPUB templates now restore discovery-backed source choices on the Discovery panel while ordinary server and manual EPUB templates stay on Server."
                ),
                AppChangelogEntry(
                    id: "apple-dogfood-pipeline-gate",
                    title: "Dogfood pipeline gate is explicit",
                    detail: "The repo now has a non-physical dogfood pipeline command that runs the local Web and Apple cross-surface checkpoint before the shared Apple pipeline verification."
                ),
                AppChangelogEntry(
                    id: "tvos-reader-header-clearance",
                    title: "TV reader header gets full width",
                    detail: "Apple TV interactive reader headers now stretch the modern book banner across the top row and reserve more vertical clearance so the original sentence starts below the header."
                ),
                AppChangelogEntry(
                    id: "apple-cross-surface-checkpoint",
                    title: "Cross-surface checkpoint gate",
                    detail: "The repo now has a non-physical checkpoint command that builds Web production and export assets, then runs Apple local-surface verification before safe pushes or explicit attended device deploys."
                ),
                AppChangelogEntry(
                    id: "create-discovery-provider-readiness",
                    title: "Create discovery readiness is clearer",
                    detail: "Web and Apple Create now keep missing backend-advertised book and video discovery providers disabled with a clear message after provider inventory loads, while preserving fallback controls before the inventory arrives."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-jump-render-target",
                    title: "Reader jumps render immediately",
                    detail: "Apple interactive reader slider, Jump To, search, chapter, and bookmark jumps now clear stale frozen transcript state and show the target sentence while audio seeks and starts playback."
                ),
                AppChangelogEntry(
                    id: "tvos-interactive-reader-header-width",
                    title: "TV reader header gets room",
                    detail: "Apple TV interactive reader headers now let the book banner stretch across the screen and reserve the measured header height so the original-language track does not render underneath it."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-target-resolver",
                    title: "Word taps use track-aware targets",
                    detail: "Apple interactive reader word taps now ask the sequence controller for the tapped track's sentence target before seeking, keeping track switches and fallback timing aligned."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-seek-stale-guard",
                    title: "Word taps rewind more reliably",
                    detail: "Apple interactive reader word taps now cancel older sequence audio transitions and drift-check same-track seeks, so tapping a word rewinds to that word without a stale track load moving playback back afterward."
                ),
                AppChangelogEntry(
                    id: "web-transcript-word-accessibility",
                    title: "Web transcript words expose playback state",
                    detail: "The Web interactive transcript now marks the active word with accessibility state and gives silent pause tokens a readable label, keeping word-sync controls clearer for assistive technologies."
                ),
                AppChangelogEntry(
                    id: "apple-pipeline-journey-list-target",
                    title: "Pipeline dry-runs are clearer",
                    detail: "The shared Apple pipeline now has an explicit app-owned journey list target, and orchestration dry-runs depend on that list plus true dry-runs so non-device preflights are easier to audit."
                ),
                AppChangelogEntry(
                    id: "apple-notification-toggle-unregisters",
                    title: "Notification toggles match the backend",
                    detail: "Apple settings now unregister the current device token when Job Notifications are turned off and skip sign-in re-registration while the toggle is disabled, so backend delivery follows the local preference."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-cross-file-rewind",
                    title: "Word taps rewind across language files",
                    detail: "Apple interactive reader word taps now reload the correct original or translation audio file when a previous combined-track seek rebuilt playback from the other file, so tapping back to a word can rewind and switch tracks reliably."
                ),
                AppChangelogEntry(
                    id: "apple-notification-signout-clears-session",
                    title: "Notifications forget signed-out sessions",
                    detail: "Apple clients now clear cached notification API state on sign-out, preventing a later push token callback from registering against a previous session."
                ),
                AppChangelogEntry(
                    id: "apple-notification-token-registration-order",
                    title: "Notifications register more reliably",
                    detail: "Apple clients now remember the authenticated API configuration before a push token arrives, so device registration works whether login or APNs registration finishes first."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-local-lane-seek",
                    title: "Word taps rewind to the intended lane",
                    detail: "Apple interactive reader word taps now normalize display sentence ids to the active chunk before seeking, and recompute tapped-lane timing when single-track playback switches between original and translation audio."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-sequence-track-seek",
                    title: "Word taps land on the tapped track",
                    detail: "Apple interactive reader word taps now compute sequence seeks from the tapped original or translation timing track directly, and combined single-track playback reloads the matching audio file before rewinding."
                ),
                AppChangelogEntry(
                    id: "apple-create-sentence-splitter-mode",
                    title: "Create can choose sentence splitting",
                    detail: "Web Narrate Ebook and Apple Create now expose the backend sentence splitter mode, preserve it in saved templates and recent-job defaults, and submit the same stable or modern pipeline override."
                ),
                AppChangelogEntry(
                    id: "interactive-reader-token-audio-mode-sync",
                    title: "Word taps switch narration cleanly",
                    detail: "Apple interactive reader word taps outside sequence mode now sync the narration mode to the tapped language track before rewinding, so original, translation, and transliteration taps land on the matching audio."
                )
            ]
}
