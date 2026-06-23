enum AppChangelogData {
    static let days: [AppChangelogDay] = [
        AppChangelogDay(
            id: "2026-06-23",
            dateLabel: "June 23, 2026",
            version: "2026.06.23.46",
            entries: [
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
