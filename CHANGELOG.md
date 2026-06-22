# ebook-tools Changelog

Daily user-visible changes for the Apple app and shared home pipeline dogfood.

## 2026-06-22

### 2026.06.22.138

- Advanced visible Apple app versioning to `v2026.06.22.138`.
- Moved Jobs row title, metadata, progress, status, and cover URL presentation helpers into `JobRowView+Presentation.swift`, keeping `JobRowView.swift` focused on row layout and platform styling.

### 2026.06.22.137

- Advanced visible Apple app versioning to `v2026.06.22.137`.
- Moved transcript track auto-scale measurement, resize handlers, and delayed fit recalculation into `InteractiveTranscriptView+AutoScale.swift`, keeping the core transcript view focused on layout composition.

### 2026.06.22.136

- Advanced visible Apple app versioning to `v2026.06.22.136`.
- Moved timeline active-display builders and active-index resolution into `TextPlayerTimeline+ActiveDisplay.swift`, keeping the base timeline builder focused on sentence runtime construction.

### 2026.06.22.135

- Advanced visible Apple app versioning to `v2026.06.22.135`.
- Moved library video preview, fullscreen presentation, tvOS video body, and video resume/progress helpers into `LibraryPlaybackView+Video.swift`, keeping the main library playback view focused on load and content state.

### 2026.06.22.134

- Advanced visible Apple app versioning to `v2026.06.22.134`.
- Moved the tvOS video playback overlay header and bottom controls into `VideoPlayerOverlayView+TVLayout.swift`, keeping the shared video overlay focused on iOS and subtitle orchestration.

### 2026.06.22.133

- Advanced visible Apple app versioning to `v2026.06.22.133`.
- Moved the tvOS transcript overlay and split-layout handlers into `InteractiveTranscriptView+TVLayout.swift`, keeping the core transcript view less platform-specific.

### 2026.06.22.132

- Advanced visible Apple app versioning to `v2026.06.22.132`.
- Moved the growing June 22 changelog entry list into `AppChangelogData+2026-06-22.swift`, leaving `AppChangelogData.swift` as the compact day index for future daily dogfood entries.

### 2026.06.22.131

- Advanced visible Apple app versioning to `v2026.06.22.131`.
- Split the public backend runtime descriptor into named auth, client config, and Apple pipeline sections, with regression coverage that every response gets fresh environment/profile lists for simulator and device preflights.

### 2026.06.22.130

- Advanced visible Apple app versioning to `v2026.06.22.130`.
- Moved iPad hardware-keyboard first-responder reclaim, software-keyboard guards, focus updates, and window-touch reclaim into `InteractivePlayerShortcutFocus.swift`, keeping shortcut support focused on controller lifecycle and key-command mapping.

### 2026.06.22.129

- Advanced visible Apple app versioning to `v2026.06.22.129`.
- Centralized text-player token reveal counts, current-token selection, and segment-end reveal tolerance into one timeline helper so live display, active sentence, and track-switch settling states use the same playback rules.

### 2026.06.22.128

- Advanced visible Apple app versioning to `v2026.06.22.128`.
- Moved text-player sentence track filtering, hidden-track controls, selection mapping, and playback shadow mapping into `TextPlayerSentenceView.swift`, keeping text player views focused on the frame shell and shared styling helpers.

### 2026.06.22.127

- Advanced visible Apple app versioning to `v2026.06.22.127`.
- Moved text-player variant headers, token flow composition, platform font sizing, seek lookup, and token color state into `TextPlayerVariantView.swift`, keeping text player views focused on frame and sentence orchestration.

### 2026.06.22.126

- Advanced visible Apple app versioning to `v2026.06.22.126`.
- Moved the reusable text-player token flow layout into `TextPlayerTokenFlowLayout.swift`, keeping text player views focused on sentence and variant composition.

### 2026.06.22.125

- Advanced visible Apple app versioning to `v2026.06.22.125`.
- Moved text-player token chip rendering, tap gestures, context menu, and dictionary lookup presenter into `TextPlayerTokenWordView.swift`, keeping text player views focused on flow and variant composition.

### 2026.06.22.124

- Advanced visible Apple app versioning to `v2026.06.22.124`.
- Moved text-player token coordinate-space and preference-key plumbing into `TextPlayerTokenGeometry.swift`, keeping text player rendering focused on sentence, variant, and token views.

### 2026.06.22.123

- Advanced visible Apple app versioning to `v2026.06.22.123`.
- Moved shortcut dispatch identity, throttling, and UIKit fallback scheduling into `InteractivePlayerShortcutDispatch.swift`, keeping iPad keyboard support focused on responder ownership and key-command wiring.

### 2026.06.22.122

- Advanced visible Apple app versioning to `v2026.06.22.122`.
- Moved the iPad hardware-keyboard GameController fallback into `InteractivePlayerShortcutHardwareFallback.swift`, keeping shortcut support focused on responder ownership and UIKit key commands.

### 2026.06.22.121

- Advanced visible Apple app versioning to `v2026.06.22.121`.
- Moved player menu pickers and selection handlers into `InteractivePlayerView+MenuControls.swift`, keeping the menu file focused on header imagery, the control bar shell, and TV text-size controls.

### 2026.06.22.120

- Advanced visible Apple app versioning to `v2026.06.22.120`.
- Moved interactive transcript composition into `InteractivePlayerView+InteractiveContent.swift`, keeping `InteractivePlayerView+Layout.swift` focused on the screen shell and overlay layers.

### 2026.06.22.119

- Advanced visible Apple app versioning to `v2026.06.22.119`.
- Moved interactive player lifecycle observers and playback side-effect handlers into `InteractivePlayerView+LifecycleObservers.swift`, keeping `InteractivePlayerView+Layout.swift` focused on screen composition.

### 2026.06.22.118

- Advanced visible Apple app versioning to `v2026.06.22.118`.
- Moved iPad hardware-keyboard input host views and the touch observer into `InteractivePlayerShortcutHostViews.swift`, keeping shortcut dispatch focused on command routing.

### 2026.06.22.117

- Advanced visible Apple app versioning to `v2026.06.22.117`.
- Moved tvOS playback focus and remote navigation handlers into `VideoPlayerOverlayTVFocus.swift`, keeping the video overlay view focused on composition and chrome rendering.

### 2026.06.22.116

- Advanced visible Apple app versioning to `v2026.06.22.116`.
- Moved subtitle selection, token frame reporting, and display-building models into `SubtitleOverlayModels.swift`, keeping `SubtitleOverlayView.swift` focused on overlay layout, gestures, and token rendering.

### 2026.06.22.115

- Advanced visible Apple app versioning to `v2026.06.22.115`.
- Moved Library playback metadata, cover, language, media selection, subtitle track, and video metadata derivation into `LibraryPlaybackMetadata.swift`, keeping `LibraryPlaybackView.swift` focused on screen lifecycle, layout, and playback actions.

### 2026.06.22.114

- Advanced visible Apple app versioning to `v2026.06.22.114`.
- Moved video overlay subtitle drag selection, phone subtitle positioning, and shared overlay labels into `VideoPlayerOverlayInteraction.swift`, keeping `VideoPlayerOverlayView.swift` focused on composition and TV focus orchestration.

### 2026.06.22.113

- Advanced visible Apple app versioning to `v2026.06.22.113`.
- Moved shared media search state, actions, pill buttons, and input controls into `MediaSearchControls.swift`, keeping `MediaSearchView.swift` focused on panel and overlay presentation.

### 2026.06.22.112

- Advanced visible Apple app versioning to `v2026.06.22.112`.
- Moved shared platform slider, picker, playback button, focus, gesture, and list-background helpers into `PlatformControls.swift`, keeping `PlatformAdapter.swift` focused on detection, metrics, typography, and colors.

### 2026.06.22.111

- Advanced visible Apple app versioning to `v2026.06.22.111`.
- Moved Settings connection, playback, changelog, voice, and notification section rendering into `PlaybackSettingsSections.swift`, keeping `PlaybackSettingsView.swift` focused on state, lifecycle, and backend descriptor checks.

### 2026.06.22.110

- Advanced visible Apple app versioning to `v2026.06.22.110`.
- Moved daily changelog entries into `AppChangelogData.swift`, keeping the shared changelog model/API small while preserving the visible changelog on iPhone, iPad, and Apple TV.

### 2026.06.22.109

- Advanced visible Apple app versioning to `v2026.06.22.109`.
- Moved linguist bubble answer rendering plus shared close/font controls into `LinguistBubbleContentControls.swift`, keeping the main bubble view focused on state, measurement, and gestures.

### 2026.06.22.108

- Advanced visible Apple app versioning to `v2026.06.22.108`.
- Moved linguist bubble picker option models and picker-data builders into `LinguistBubblePickerModels.swift`, keeping `LinguistBubblePickerUI.swift` focused on overlay rendering.

### 2026.06.22.107

- Advanced visible Apple app versioning to `v2026.06.22.107`.
- Split iOS and tvOS linguist bubble header controls into platform-specific SwiftUI extension files while keeping shared selector menus in the common header controls file.

### 2026.06.22.106

- Advanced visible Apple app versioning to `v2026.06.22.106`.
- Moved linguist bubble header rows and selector controls into `LinguistBubbleHeaderControls.swift`, keeping the main bubble view focused on state, lifecycle, and content.
- Reworked the tvOS changelog into a deterministic focus-paged entry window so the Siri Remote can move through older daily entries without relying on nested scroll gesture handling.

### 2026.06.22.105

- Advanced visible Apple app versioning to `v2026.06.22.105`.
- Moved linguist bubble model/voice label parsing and model grouping out of the main SwiftUI view into the shared text utilities file, keeping the bubble view focused on layout and controls.

### 2026.06.22.104

- Advanced visible Apple app versioning to `v2026.06.22.104`.
- Added non-secret Apple pipeline identity metadata to the backend runtime descriptor and made the shared backend checker assert the ebook-tools manifest id.
- Reworked the tvOS visible changelog into compact rows inside a real bounded scroll view with focus-following movement, a wider login card, and an up/down position affordance so the Siri Remote can reveal older daily entries.

### 2026.06.22.103

- Advanced visible Apple app versioning to `v2026.06.22.103`.
- Reused the shared video time formatter for TV playback scrubber labels instead of keeping a duplicate formatter inside the tvOS controls view.

### 2026.06.22.102

- Advanced visible Apple app versioning to `v2026.06.22.102`.
- Moved the TV playback timeline pill into the tvOS playback controls module so the overlay stays focused on layout and focus orchestration.

### 2026.06.22.101

- Advanced visible Apple app versioning to `v2026.06.22.101`.
- Moved the tvOS changelog visible-row, position-label, and remote-movement calculations into one focused helper so full-day changelog scrolling remains predictable as daily entries grow.

### 2026.06.22.100

- Advanced visible Apple app versioning to `v2026.06.22.100`.
- Made the tvOS login and settings changelog use the bounded remote-scroll list for the full current-day changelog, with a position counter proving the Siri Remote can move beyond the first visible rows.

### 2026.06.22.99

- Advanced visible Apple app versioning to `v2026.06.22.99`.
- Hardened the tvOS changelog remote-scroll regression so it tracks the newest daily entry automatically and keeps proving older rows can be revealed after future version bumps.

### 2026.06.22.98

- Advanced visible Apple app versioning to `v2026.06.22.98`.
- Split the Apple API client endpoint methods into focused Auth, Library/Jobs, Linguist, Notification, Pipeline Media, and Playback State service extensions while keeping shared transport/auth handling centralized.

### 2026.06.22.97

- Advanced visible Apple app versioning to `v2026.06.22.97`.
- Split Pipeline sentence metadata and job timing API payloads into dedicated model files so media file/chunk decoding is no longer coupled to timed-text contracts.

### 2026.06.22.96

- Advanced visible Apple app versioning to `v2026.06.22.96`.
- Made the tvOS daily changelog in login and settings use capped, remote-focusable rows so the Siri Remote can move through entries beyond the first visible rows.
- Added a DEBUG-only E2E launch flag so simulator UI tests can force the login surface without reusing stored sessions.
- Moved Library browse and Pipeline job status/progress API models into a dedicated Models file, leaving the broad API model file focused on generic JSON and media metadata helpers.

### 2026.06.22.94

- Advanced visible Apple app versioning to `v2026.06.22.94`.
- Moved assistant lookup, structured linguist, model list, voice inventory, and audio synthesis API models into a dedicated Models file.

### 2026.06.22.93

- Advanced visible Apple app versioning to `v2026.06.22.93`.
- Moved login, session, OAuth, and backend runtime descriptor API models into a dedicated Models file so authentication contract decoding is separated from unrelated API payloads.

### 2026.06.22.92

- Advanced visible Apple app versioning to `v2026.06.22.92`.
- Moved pipeline media, chunk sentence, audio-track, and timing API models into a dedicated Models file so media playback decoding no longer lives in the broad API model file.

### 2026.06.22.91

- Advanced visible Apple app versioning to `v2026.06.22.91`.
- Moved reading-bed, bookmark, and resume-position API models into a dedicated Models file so playback state decoding no longer lives in the broad API model file.

### 2026.06.22.90

- Advanced visible Apple app versioning to `v2026.06.22.90`.
- Moved push-notification API request and response models into a dedicated Models file so notification registration and preference decoding no longer live in the broad API model file.

### 2026.06.22.89

- Advanced visible Apple app versioning to `v2026.06.22.89`.
- Moved lookup-cache API response models into a dedicated Models file so dictionary cache decoding no longer lives in the broad API model file.

### 2026.06.22.88

- Advanced visible Apple app versioning to `v2026.06.22.88`.
- Moved media-search API response models into a dedicated Models file so the large shared API model file no longer owns search-specific decoding and logging.

### 2026.06.22.87

- Advanced visible Apple app versioning to `v2026.06.22.87`.
- Moved media-search async search state and result-target calculations into a dedicated view-model source file so the SwiftUI search view stays focused on controls and layout.

### 2026.06.22.86

- Advanced visible Apple app versioning to `v2026.06.22.86`.
- Moved media-search result display models, result lists, and result rows into a dedicated SwiftUI file so search orchestration is separated from result presentation.

### 2026.06.22.85

- Advanced visible Apple app versioning to `v2026.06.22.85`.
- Moved the interactive player keyboard shortcut help overlay into its own SwiftUI source file so input bridge code no longer carries overlay layout and keycap rendering.

### 2026.06.22.84

- Advanced visible Apple app versioning to `v2026.06.22.84`.
- Moved backwards-compatible MyLinguist/Video linguist bubble state and wrapper adapters into their own SwiftUI compatibility file, leaving the core bubble view focused on layout and interaction.

### 2026.06.22.83

- Advanced visible Apple app versioning to `v2026.06.22.83`.
- Moved shared row metadata traversal and nested-path lookup into a dedicated helper so Jobs and Library rows no longer carry duplicate recursive parsing code.
- Made the TV changelog respond directly to Siri Remote up/down moves so the bounded daily log can scroll past the first visible rows.

### 2026.06.22.82

- Advanced visible Apple app versioning to `v2026.06.22.82`.
- Moved job-row YouTube thumbnail parsing and cover URL normalization into a dedicated helper so the SwiftUI row view stays focused on row state and layout.

### 2026.06.22.81

- Advanced visible Apple app versioning to `v2026.06.22.81`.
- Moved the library row compact and landscape shells into the shared library-row components file so browsing row layout matches the job row pattern.

### 2026.06.22.80

- Advanced visible Apple app versioning to `v2026.06.22.80`.
- Moved the job row compact and landscape shells into the shared job-row components file so responsive row layout is separated from metadata and cover-resolution logic.

### 2026.06.22.79

- Advanced visible Apple app versioning to `v2026.06.22.79`.
- Moved the library playback header, loading, error, unavailable, and image-reel chrome into a dedicated SwiftUI file so the playback view stays focused on orchestration and resume behavior.

### 2026.06.22.78

- Advanced visible Apple app versioning to `v2026.06.22.78`.
- Added a backend runtime descriptor guard so the public Apple pipeline preflight contract rejects secret-like metadata keys close to the helper that builds it.

### 2026.06.22.77

- Advanced visible Apple app versioning to `v2026.06.22.77`.
- Made TV changelog rows individually focusable so the Siri Remote can move down through the full daily change list instead of stopping after the first visible lines.

### 2026.06.22.76

- Advanced visible Apple app versioning to `v2026.06.22.76`.
- Moved shared language flag roles, entries, and resolver tables into a dedicated Swift source file.

### 2026.06.22.75

- Advanced visible Apple app versioning to `v2026.06.22.75`.
- Moved shared player glyph marks and cover artwork stack into a dedicated SwiftUI source file.

### 2026.06.22.74

- Advanced visible Apple app versioning to `v2026.06.22.74`.
- Moved shared player language flag row and badge UI into a dedicated SwiftUI source file.

### 2026.06.22.73

- Advanced visible Apple app versioning to `v2026.06.22.73`.
- Made the TV changelog summary a focusable, bounded scroll area so the Siri Remote can reveal the full daily entry list.

### 2026.06.22.72

- Advanced visible Apple app versioning to `v2026.06.22.72`.
- Moved shared player channel variants and metrics out of the visual channel badge file.

### 2026.06.22.71

- Advanced visible Apple app versioning to `v2026.06.22.71`.
- Moved job-type glyph mapping out of the shared channel badge UI file.

### 2026.06.22.70

- Advanced visible Apple app versioning to `v2026.06.22.70`.
- Moved MyLinguist preference keys and TTS voice storage out of the channel badge UI file.

### 2026.06.22.69

- Advanced visible Apple app versioning to `v2026.06.22.69`.
- Moved the visible changelog summary UI into its own Swift source file.

### 2026.06.22.68

- Advanced visible Apple app versioning to `v2026.06.22.68`.
- Moved the iPad browse-list collapse gesture helper into its own Swift source file.

### 2026.06.22.67

- Advanced visible Apple app versioning to `v2026.06.22.67`.
- Moved shared browse resume helpers into their own Swift source file.

### 2026.06.22.66

- Advanced visible Apple app versioning to `v2026.06.22.66`.
- Moved browse resume/iCloud snapshot refresh into a shared provider used by Jobs, Library, and Search.

### 2026.06.22.65

- Advanced visible Apple app versioning to `v2026.06.22.65`.
- Moved the public backend runtime descriptor into a dedicated helper with direct contract coverage for Apple pipeline preflights.

### 2026.06.22.64

- Advanced visible Apple app versioning to `v2026.06.22.64`.
- Moved browse resume notification filtering and resume-availability checks into shared helpers used by Jobs, Library, and Search.

### 2026.06.22.63

- Advanced visible Apple app versioning to `v2026.06.22.63`.
- Moved shared browse resume badge and context-menu label formatting into one formatter used by Jobs, Library, and Search.

### 2026.06.22.62

- Advanced visible Apple app versioning to `v2026.06.22.62`.
- Moved the iPad browse list collapse gesture into one shared SwiftUI modifier used by both Jobs and Library lists.

### 2026.06.22.61

- Advanced visible Apple app versioning to `v2026.06.22.61`.
- Moved job playback video-player wiring into one shared SwiftUI helper across preview, fullscreen, and tvOS playback paths.

### 2026.06.22.60

- Advanced visible Apple app versioning to `v2026.06.22.60`.
- Moved library playback video-player wiring into one shared SwiftUI helper across preview, fullscreen, and tvOS playback paths.

### 2026.06.22.59

- Advanced visible Apple app versioning to `v2026.06.22.59`.
- Moved shared player language flag row items into a dedicated SwiftUI subview with a stable row layout.

### 2026.06.22.58

- Advanced visible Apple app versioning to `v2026.06.22.58`.
- Made interactive player audio track mode changes atomic so toggling original/translation audio cannot publish a transient no-track state.

### 2026.06.22.57

- Advanced visible Apple app versioning to `v2026.06.22.57`.
- Moved tvOS jobs offline menu actions into named SwiftUI handlers.

### 2026.06.22.56

- Advanced visible Apple app versioning to `v2026.06.22.56`.
- Moved tvOS library offline menu actions into named SwiftUI handlers.

### 2026.06.22.55

- Advanced visible Apple app versioning to `v2026.06.22.55`.
- Moved interactive player header language flag rows into one SwiftUI helper with a named role-toggle handler.

### 2026.06.22.54

- Advanced visible Apple app versioning to `v2026.06.22.54`.
- Moved shared player language flag role toggles into a named SwiftUI handler.

### 2026.06.22.53

- Advanced visible Apple app versioning to `v2026.06.22.53`.
- Moved shared media search result row selection into a named SwiftUI handler.

### 2026.06.22.52

- Advanced visible Apple app versioning to `v2026.06.22.52`.
- Moved shared media search submit events into a named SwiftUI handler.

### 2026.06.22.51

- Advanced visible Apple app versioning to `v2026.06.22.51`.
- Moved shared media search clear and dismiss buttons into named SwiftUI handlers.

### 2026.06.22.50

- Advanced visible Apple app versioning to `v2026.06.22.50`.
- Moved interactive header timeline taps and tvOS header long-press toggles into named SwiftUI handlers.

### 2026.06.22.49

- Advanced visible Apple app versioning to `v2026.06.22.49`.
- Moved iPhone transcript bubble backdrop and content tap handling into named SwiftUI handlers.

### 2026.06.22.48

- Advanced visible Apple app versioning to `v2026.06.22.48`.
- Moved iPad split transcript bubble backdrop and content tap handling into named SwiftUI handlers.

### 2026.06.22.47

- Advanced visible Apple app versioning to `v2026.06.22.47`.
- Moved interactive text-player bookmark menu add, jump, and remove rows into named SwiftUI helpers.

### 2026.06.22.46

- Advanced visible Apple app versioning to `v2026.06.22.46`.
- Moved interactive text-player tvOS directional navigation into named SwiftUI focus handlers.

### 2026.06.22.45

- Advanced visible Apple app versioning to `v2026.06.22.45`.
- Moved tvOS overlay header, bubble, and timeline-pill focus events into named SwiftUI handlers.

### 2026.06.22.44

- Advanced visible Apple app versioning to `v2026.06.22.44`.
- Moved tvOS playback button, scrubber, and controls-bar focus events into named SwiftUI handlers.

### 2026.06.22.43

- Advanced visible Apple app versioning to `v2026.06.22.43`.
- Moved bookmark ribbon menu add, jump, and remove rows into named SwiftUI helpers.

### 2026.06.22.42

- Advanced visible Apple app versioning to `v2026.06.22.42`.
- Moved video bookmark menu jump and remove rows into named SwiftUI helpers.

### 2026.06.22.41

- Advanced visible Apple app versioning to `v2026.06.22.41`.
- Moved video subtitle settings close, segment, and track selection work into named SwiftUI handlers.

### 2026.06.22.40

- Advanced visible Apple app versioning to `v2026.06.22.40`.
- Moved shared video speed menu rate rows and selection work into named SwiftUI helpers.

### 2026.06.22.39

- Advanced visible Apple app versioning to `v2026.06.22.39`.
- Moved interactive player menu rows for audio, speed, reading-bed, and settings commands into named SwiftUI helpers.
- Updated the shared Apple pipeline rule so physical device installs are attended and only run when explicitly requested for a named device.

### 2026.06.22.38

- Advanced visible Apple app versioning to `v2026.06.22.38`.
- Moved iPad interactive player keyboard shortcut commands into named SwiftUI handlers.

### 2026.06.22.37

- Advanced visible Apple app versioning to `v2026.06.22.37`.
- Moved interactive player music-picker, bookmark-identity, and reading-bed URL reactions into named SwiftUI handlers.

### 2026.06.22.36

- Advanced visible Apple app versioning to `v2026.06.22.36`.
- Moved interactive transcript bubble geometry and iPad split layout updates into named SwiftUI handlers.

### 2026.06.22.35

- Advanced visible Apple app versioning to `v2026.06.22.35`.
- Moved subtitle overlay token-frame preference and clear-state updates into named SwiftUI handlers.

### 2026.06.22.34

- Advanced visible Apple app versioning to `v2026.06.22.34`.
- Moved text-player token-frame and tap-exclusion preference changes into named SwiftUI handlers.

### 2026.06.22.33

- Advanced visible Apple app versioning to `v2026.06.22.33`.
- Moved text-player visible and hidden track header toggles into named SwiftUI handlers.

### 2026.06.22.32

- Advanced visible Apple app versioning to `v2026.06.22.32`.
- Moved text and video shortcut-help overlay backdrop and close-button dismissals into named SwiftUI handlers.

### 2026.06.22.31

- Advanced visible Apple app versioning to `v2026.06.22.31`.
- Moved Jobs and Library browse row taps plus tvOS filter long-press refresh actions into named SwiftUI handlers.

### 2026.06.22.30

- Advanced visible Apple app versioning to `v2026.06.22.30`.
- Moved tvOS transcript track tap and long-press focus actions into named SwiftUI handlers.

### 2026.06.22.29

- Advanced visible Apple app versioning to `v2026.06.22.29`.
- Moved video overlay subtitle settings, phone bubble backdrop, playback-change, token-frame, and subtitle drag work into named SwiftUI handlers.

### 2026.06.22.28

- Advanced visible Apple app versioning to `v2026.06.22.28`.
- Moved Jobs and Library browse row selection, delete, search, and tvOS offline menu work into named SwiftUI handlers.

### 2026.06.22.27

- Advanced visible Apple app versioning to `v2026.06.22.27`.
- Moved playback host fullscreen video dismissal, edge-swipe back, and preview drag work into named SwiftUI handlers.

### 2026.06.22.26

- Advanced visible Apple app versioning to `v2026.06.22.26`.
- Centralized backend request session-token parsing for Authorization headers and `access_token` query fallback.

### 2026.06.22.25

- Advanced visible Apple app versioning to `v2026.06.22.25`.
- Moved bookmark ribbon add, jump, remove, and tvOS focus movement work into named SwiftUI handlers.

### 2026.06.22.24

- Advanced visible Apple app versioning to `v2026.06.22.24`.
- Moved tvOS Library and Jobs offline menu remove/download commands into named SwiftUI handlers.

### 2026.06.22.23

- Advanced visible Apple app versioning to `v2026.06.22.23`.
- Matched the Library browse list to the Jobs row-builder structure so iPad and tvOS row actions are easier to audit.

### 2026.06.22.22

- Advanced visible Apple app versioning to `v2026.06.22.22`.
- Moved offline download, retry, and remove-copy menu work into named SwiftUI handlers.

### 2026.06.22.21

- Advanced visible Apple app versioning to `v2026.06.22.21`.
- Moved Apple Music picker dismiss, authorization, search, clear, stop, tab, suggestion-load, and result-selection work into named SwiftUI handlers.

### 2026.06.22.20

- Advanced visible Apple app versioning to `v2026.06.22.20`.
- Moved interactive text search overlay toggle, dismiss, submit, query-change, and result-selection work into named SwiftUI handlers.

### 2026.06.22.19

- Advanced visible Apple app versioning to `v2026.06.22.19`.
- Moved video search overlay toggle, dismiss, submit, query-change, and result-selection work into named SwiftUI handlers.

### 2026.06.22.18

- Advanced visible Apple app versioning to `v2026.06.22.18`.
- Moved interactive player and video bookmark menu commands plus remote bookmark create/delete work into named SwiftUI handlers.

### 2026.06.22.17

- Advanced visible Apple app versioning to `v2026.06.22.17`.
- Moved interactive player menu selection, playback-rate, reading-bed, text-size, seek, and voice-reset commands into named SwiftUI handlers.

### 2026.06.22.16

- Advanced visible Apple app versioning to `v2026.06.22.16`.
- Moved background music overlay transport, volume, scrubbing, and song-selection commands into named SwiftUI handlers.

### 2026.06.22.15

- Advanced visible Apple app versioning to `v2026.06.22.15`.
- Moved Jobs and Library browse list lifecycle, resume-store updates, and sidebar-collapse drag handling into named SwiftUI handlers.

### 2026.06.22.14

- Advanced visible Apple app versioning to `v2026.06.22.14`.
- Moved combined browse search focus, resume-store updates, search clearing, and result selection into named SwiftUI handlers.

### 2026.06.22.13

- Advanced visible Apple app versioning to `v2026.06.22.13`.
- Moved shared media search submit, clear, dismiss, result-selection, tvOS focus, and async search/debounce work into named SwiftUI handlers.

### 2026.06.22.12

- Advanced visible Apple app versioning to `v2026.06.22.12`.
- Moved transcript audio-duration recording, auto-scale measurement, bubble-change recalculation, playback cleanup, and disappear cleanup into named SwiftUI lifecycle handlers.

### 2026.06.22.11

- Advanced visible Apple app versioning to `v2026.06.22.11`.
- Moved job and library playback host lifecycle work into named SwiftUI handlers so load, start-over, now-playing, scene-phase, and teardown reactions are easier to audit on iPad and tvOS.

### 2026.06.22.10

- Advanced visible Apple app versioning to `v2026.06.22.10`.
- Moved video player setup, URL-change, subtitle, bookmark, and playback state reactions into named SwiftUI lifecycle handlers so iPad and tvOS playback changes are easier to review.

### 2026.06.22.09

- Advanced visible Apple app versioning to `v2026.06.22.09`.
- Removed tvOS video control menu type erasure so bookmark and playback speed menus stay concrete SwiftUI views through the focusable controls bar.

### 2026.06.22.08

- Advanced visible Apple app versioning to `v2026.06.22.08`.
- Removed transcript track layout type erasure so phone, iPad split, and tvOS transcript branches pass the measured track view through typed SwiftUI helpers.

### 2026.06.22.07

- Advanced visible Apple app versioning to `v2026.06.22.07`.
- Replaced the interactive player layout's erased lifecycle `AnyView` chain with staged typed SwiftUI modifiers and named playback/header handlers.

### 2026.06.22.06

- Advanced visible Apple app versioning to `v2026.06.22.06`.
- Replaced the interactive player header overlay's erased `AnyView` branch with typed SwiftUI builders while preserving the existing phone, iPad, and tvOS header layouts.

### 2026.06.22.05

- Advanced visible Apple app versioning to `v2026.06.22.05`.
- Replaced the browse shell's erased `AnyView` section picker handoff with a typed SwiftUI `BrowseSectionPicker` shared by Jobs, Library, Search, and Settings.

### 2026.06.22.04

- Advanced visible Apple app versioning to `v2026.06.22.04`.
- Split release version metadata and in-app changelog rendering out of `AppTheme.swift` into focused Shared SwiftUI files.
- Hardened MacBook backend test setup so pytest uses a local HuggingFace cache when external model storage is offline, while production runtime paths still fail visibly if misconfigured.

### 2026.06.22.03

- Advanced visible Apple app versioning to `v2026.06.22.03`.
- Refactored Library and Jobs row actions so selection, delete, and move-to-library commands route through named SwiftUI methods instead of inline row-builder closures.

### 2026.06.22.02

- Advanced visible Apple app versioning to `v2026.06.22.02`.
- Refactored the Apple browse shell so refresh, selection, search, sign-out, and split-view navigation are handled by named SwiftUI actions instead of inline view-builder closures.

### 2026.06.22.01

- Advanced visible Apple app versioning to `v2026.06.22.01`.
- Added token-safe backend auth/session duration metrics so slow login reports can be diagnosed from Prometheus without exposing credentials or session tokens.

## 2026-06-21

### 2026.06.21.11

- Advanced visible Apple app versioning to `v2026.06.21.11`.
- Moved root notification, keyboard-shortcut, session-restore, and offline sync lifecycle hooks into focused SwiftUI modifiers so the app shell is easier to iterate safely across iPhone, iPad, and tvOS.

### 2026.06.21.10

- Advanced visible Apple app versioning to `v2026.06.21.10`.
- Hardened the in-app version badge so iPad browse/login headers render the release text inside an explicit fixed-size shape instead of accepting narrow text proposals.
- Kept the shared pipeline rule that simulator runtimes must match detected physical device OS versions across ebook-tools and Finance Review.

### 2026.06.21.09

- Advanced visible Apple app versioning to `v2026.06.21.09`.
- Refactored Settings into focused connection, playback, changelog, voice, and notification sections so iPad and tvOS review surfaces can evolve with less layout risk.
- Restored the compact browse version chip to a journey-verified 96 pt width after the iPad geometry guard caught a too-narrow badge proposal.

### 2026.06.21.08

- Advanced visible Apple app versioning to `v2026.06.21.08`.
- Aligned ebook-tools with the shared WD staging convention at `/Volumes/WD-1TB/Data/staging/ebook-tools`, matching the Finance Review dogfood runtime staging path before backend maintenance.
- Updated the shared Apple pipeline manifest/docs/tests so both dogfood apps use storage preflights before disk-heavy Mac Studio work.

### 2026.06.21.07

- Replaced the compact browse-header version text with the short build token `b07`, while keeping the full `v2026.06.21.07` in login, Settings, changelog, metadata, and accessibility.
- Locked the compact badge to a fixed one-line text proposal so constrained iPad sidebars cannot stack release characters vertically.

### 2026.06.21.06

- Replaced the compact iPad header pill with a shorter fixed-width chip so `v2026.06.21.06` cannot collapse into vertical characters in split view.
- Switched version badge text to fixed-size monospaced rendering with an explicit chip width instead of relying on SwiftUI's compressed text proposal.

### 2026.06.21.05

- Hardened version badge layout so `v2026.06.21.05` owns its text width before decoration and cannot collapse into a tall narrow shape.
- Split crowded iPad browse headers into stable brand/account and status/action rows so toolbar controls do not squeeze the version.
- Let changelog headers fall back to a vertical title/date stack instead of compressing the full daily version label.

### 2026.06.21.04

- Reworked the login/header version badge so `v2026.06.21.04` owns enough horizontal space and cannot collapse into vertically stacked characters on iPad.
- Switched compact toolbar headers to `v06.21.04` while keeping the full daily version in the login and changelog surfaces.

### 2026.06.21.03

- Fixed the iPad release badge so `v2026.06.21.03` stays as a single horizontal pill in crowded headers.
- Aligned Apple bundle metadata with the daily release so device inventory can report `2026.6.21 (2026062103)` instead of `1.0 (1)`.

### 2026.06.21.02

- Added a release-version contract check that keeps iOS/tvOS Info plists, in-app changelog data, Markdown changelog, and journey assertions aligned.
- Advanced the visible Apple app release badge to `v2026.06.21.02`.

### 2026.06.21.01

- Added visible release versioning across iPhone, iPad, and Apple TV surfaces with `v2026.06.21.01`.
- Added an in-app daily changelog summary on login and in Settings.
- Added Settings connection evidence for API host, signed-in session, Keychain token storage, and backend runtime descriptor status.
- Added the public backend runtime descriptor at `/api/system/runtime` so simulator and device workflows can verify the expected service without credentials.
- Added shared pipeline backend preflight checks for `/_health` and `/api/system/runtime`.
- Added app-owned journey assertions for stable navigation surfaces, Settings connection rows, changelog visibility, and visible version badge.
- Added Apple TV dogfood recovery guidance for reboot, clean reinstall, and manual launch after CoreDevice or tvOS foreground-state issues.
