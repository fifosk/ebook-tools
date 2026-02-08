# ebook-tools User Guide

This guide covers day-to-day use of ebook-tools from the web interface, iOS, and tvOS apps. It assumes the system is already deployed and you have a user account.

---

## Table of Contents

1. [Signing In](#signing-in)
2. [Dashboard Overview](#dashboard-overview)
3. [Theme and Appearance](#theme-and-appearance)
4. [Library](#library)
5. [Processing a Book](#processing-a-book)
6. [Job Overview](#job-overview)
7. [Interactive Player](#interactive-player)
8. [MyLinguist Dictionary](#mylinguist-dictionary)
9. [Sentence Images and MyPainter](#sentence-images-and-mypainter)
10. [Subtitle Translation](#subtitle-translation)
11. [YouTube Video](#youtube-video)
12. [Video Dubbing](#video-dubbing)
13. [iOS and tvOS Apps](#ios-and-tvos-apps)
14. [Administration](#administration)
15. [Account Settings](#account-settings)
16. [Troubleshooting](#troubleshooting)

---

## Signing In

Open the ebook-tools web interface in your browser. You will see a sign-in form with username and password fields.

Enter the credentials provided by your administrator and select **Sign in**. If OAuth providers (Google or Apple) are configured, you will also see buttons to register or sign in with those services below the password form.

Your session persists across browser tabs and survives page refreshes. The session token is stored in your browser until you explicitly sign out or the token expires.

If you see an error after signing in, verify that your account is active. Suspended or inactive accounts cannot sign in. Contact your administrator if you need your account reactivated.

---

## Dashboard Overview

After signing in, the dashboard appears with two main areas: a **sidebar** on the left and the **main content area** on the right.

### Sidebar

The sidebar is the primary navigation tool. It contains the following sections:

**Player** -- At the top of the sidebar, the Player button opens the interactive player for the currently selected job. When a job is selected, the button shows the job name, target language flag, and processing status.

**Browse library** -- Opens the library view where you can browse all processed books and media.

**Audiobooks** (visible to users with scheduling permissions):
- **Book Page** -- The multi-step book narration wizard for processing new ebooks.
- **Create Audiobook** -- An alternative streamlined form for creating audiobook jobs.

**Videos** (visible to users with scheduling permissions):
- **Subtitles** -- Translate subtitle files into other languages.
- **YouTube Video** -- Download YouTube videos and their subtitle tracks.
- **Dub Video** -- Generate dubbed audio tracks for videos.

**Job Overview** -- Lists all active and recent jobs grouped by type (Audiobooks, Subtitles, Videos). Each job shows its name, target language flag, processing progress percentage, and status indicator. Click a job to view its progress details. Click the play button next to a job to open it directly in the interactive player.

**Administration** (visible to admin users only):
- **User management** -- Create and manage user accounts.
- **Reading music** -- Upload and manage background music tracks for the player.
- **Settings** -- System configuration, backups, and server settings.
- **System** -- Monitor server status, reload configuration, and manage restarts.

### Account Panel

At the bottom of the sidebar, your account panel shows your name, username, and role. Expanding it reveals:
- **Change password** -- Update your current password.
- **Theme** -- Select a visual theme (see below).
- **Sign out** -- End your session.

---

## Theme and Appearance

ebook-tools offers four visual themes. You can switch themes from the account panel in the sidebar.

- **Light** -- Bright surfaces with dark text, best for daytime use.
- **Dark** -- Dim surfaces with light text, reduces glare in low-light environments.
- **Magenta** -- A high-contrast magenta palette with vibrant accents.
- **System** -- Automatically follows your operating system's light or dark mode preference. When active, a hint below the selector shows which mode is currently applied.

Your theme preference is saved in your browser and persists across sessions.

---

## Library

The library is where you browse all processed books, dubbed videos, and translated subtitles that have been moved to the library.

### Browsing

The library displays items as cards with cover images, titles, authors, and language flags. Four view modes are available:

- **All** -- A flat list of every item.
- **By Author** -- Groups items by author name.
- **By Genre** -- Groups items by genre.
- **By Language** -- Groups items by target language.

Switch between views using the buttons in the toolbar.

### Searching

Use the search bar at the top to filter by author, title, genre, or language. The search is instant and filters as you type.

### Opening Items

Click any library item to open it in the interactive player. The player loads the processed media and is ready for playback immediately.

### Library Management

- **Refresh** -- Reloads the library list from the server.
- **Reindex library** -- Scans the storage directory and rebuilds the library index. Use this if items are missing after manual file changes.

---

## Processing a Book

The Book Page is a multi-tab wizard for submitting new ebook processing jobs. Each tab configures a different aspect of the job.

### Source

Select the EPUB file to process. You have two options:

- **Browse** -- Pick an EPUB from the server's configured ebook directory (NAS library). A file browser dialog shows available files.
- **Upload** -- Drag and drop an EPUB file onto the upload area, or click to browse your local files.

After selecting a file, the output path is automatically derived from the filename. You can override it if needed.

You can also specify a sentence range if you only want to process part of the book:
- **Start sentence** -- The first sentence to process (default: 1).
- **End sentence** -- The last sentence to process (leave blank for the entire book).

If you have processed this book before, the start sentence automatically picks up where your last job left off.

**Chapter selection** -- If the EPUB contains chapter metadata, you can switch to chapter-based selection and check individual chapters to process instead of specifying sentence numbers.

### Metadata

This tab lets you attach book metadata (title, author, genre, cover image) to the job. Metadata appears in the library and player.

- **Lookup** -- Search Open Library by title or ISBN to auto-fill metadata. No API key is required.
- **Manual edit** -- Edit the metadata JSON directly.
- **Cover image** -- Extracted automatically from the EPUB if available, or fetched from Open Library.

### Language and Translation

Configure the languages for your narrated book:

- **Source language** -- The language the EPUB is written in (default: English).
- **Target languages** -- One or more languages to translate into. Select from the dropdown or type a custom language. Over 80 languages are supported, including Arabic, Chinese, Hindi, Japanese, Korean, Russian, and many more.
- **Translation provider** -- Choose between:
  - **LLM** (default) -- Uses a large language model for higher-quality, more natural translations.
  - **Google Translate** -- Fast machine translation via the Google Translate API.
- **Transliteration** -- When enabled, generates romanized or phonetic transliterations alongside translations. Useful for languages with non-Latin scripts (Arabic, Chinese, Hindi, Japanese, etc.).

### Output and Narration

Control how the narrated output sounds:

- **Audio mode** -- Determines what is narrated in each audio segment:
  - Mode 1: Only the translated sentence.
  - Mode 2: Sentence number followed by the translated sentence.
  - Mode 3: Numbering, original sentence, and translation.
  - Mode 4 (default): Original sentence followed by the translated sentence.

- **Voice** -- Select the text-to-speech voice:
  - **Google TTS (gTTS)** -- Cross-platform default, works everywhere.
  - **Piper TTS (auto)** -- Fast local neural TTS that auto-selects a voice for the target language.
  - **macOS voices** -- System voices from macOS (auto, female, or male). Only available when the backend runs on macOS.

- **Voice overrides** -- Set different voices per language when processing into multiple target languages.

- **Tempo** -- Adjust the reading speed (default: 1.0x).

- **Audio quality** -- MP3 bitrate from 64 kbps (smallest files) to 320 kbps (highest quality). The default of 96 kbps works well for speech.

- **Sentences per chunk** -- How many sentences to group into each output chunk (default: 10). Smaller chunks load faster in the player.

### Images

Optionally generate AI illustrations for each sentence in the book.

- **Enable sentence images** -- Toggle image generation on or off.

- **Image style** -- Choose a visual style for generated images:
  - **Photorealistic** -- Cinematic film-still look (slowest, highest fidelity).
  - **Comics** -- Graphic novel panel style with ink lines and halftone shading.
  - **Children's book** -- Soft watercolor storybook illustration with warm pastels.
  - **Wireframe** -- Blueprint-style monochrome line drawing (fastest).

- **Prompt pipeline** -- How the AI generates image prompts:
  - **Prompt plan** -- Uses the style template and batch processing for prompt generation.
  - **Visual canon** -- Builds a visual continuity map with character and scene tracking for more consistent imagery across the book.

- **Context sentences** -- How many surrounding sentences to include when generating each image prompt (default: 2). More context produces images that better reflect the narrative.

- **Image quality slider** -- Controls diffusion steps. Higher quality takes longer per image.

- **Image API nodes** -- Select which image generation servers to use. The system can distribute work across multiple nodes, each with an availability indicator.

### Performance Tuning

Adjust processing parameters to match your server's capacity:

- **Thread count** -- Number of parallel processing threads.
- **Queue size** -- Maximum items in the processing queue.
- **Job workers** -- Parallel workers for the job pipeline.
- **Image concurrency** -- How many images to generate simultaneously when image generation is enabled.

Leave these blank to use the server's default values.

### Submitting

The submit button is available from any tab. A callout at the top lists any missing requirements (such as an input file or target language). Once all requirements are met, click **Submit job** to enqueue the processing job.

After submission, you are taken to the Job Overview where you can monitor progress.

---

## Job Overview

The Job Overview shows the status and progress of all processing jobs.

### Job Card

Each job displays:

- **Job name** -- Derived from the book title, filename, or label.
- **Job type badge** -- Icon indicating book, subtitle, or video dubbing.
- **Language flags** -- Target language(s) for the job.
- **Status indicator** -- Current state: pending, running, completed, failed, paused, or cancelled.
- **Progress percentage** -- For running jobs, a real-time percentage updated via server-sent events (SSE). No page refresh is needed.
- **Stage indicators** -- Additional status icons for specific pipeline stages like stitching or NAS mirroring.

### Job Actions

Depending on the job's state, the following actions are available:

- **Pause** -- Temporarily halt a running job.
- **Resume** -- Continue a paused job from where it stopped.
- **Cancel** -- Stop a running job. Partial output is preserved.
- **Delete** -- Remove the job and its output files.
- **Restart** -- Re-run a completed or failed job.
- **Copy settings** -- Duplicate the job's configuration into a new Book Page form for re-submission with modifications.
- **Move to library** -- Add a completed job's output to the library for browsing.

### Live Progress

While a job is running, the progress card shows real-time updates streamed from the server:

- **Sentence progress** -- Number of sentences processed out of total.
- **Translation progress** -- Translation completion when applicable.
- **Image generation progress** -- When images are enabled, shows generated count versus expected total.
- **Playable assets** -- Indicates how many sentences have fully exported and are ready for playback (you can start listening before the job finishes).

---

## Interactive Player

The interactive player is the core feature of ebook-tools. It provides a synchronized reading and listening experience with word-level highlighting.

### Opening the Player

There are several ways to open the player:

- Click the **Player** button in the sidebar (plays the currently selected job).
- Click the **play** button next to any job in the Job Overview.
- Click any item in the **Library**.
- Jobs that are still processing can be played in real-time as sentences finish exporting.

### Layout

The player displays:

- **Text panel** -- Shows the current chunk of sentences with up to three text tracks:
  - **Original** -- The source language text.
  - **Transliteration** -- Romanized or phonetic rendering (if enabled).
  - **Translation** -- The target language text.
- **Image reel** (optional) -- A horizontal strip of AI-generated sentence images above the text.
- **Navigation controls** -- Playback buttons and sliders below the text.
- **MyLinguist bubble** (on demand) -- A floating dictionary panel that appears when you click a word.

### Playback Controls

The primary navigation bar provides:

- **First / Previous / Play-Pause / Next / Last** -- Navigate between chunks.
- **Fullscreen** -- Enter or exit fullscreen mode.
- **Original audio toggle** -- Enable or disable the original language audio track.
- **Translation audio toggle** -- Enable or disable the translation language audio track.
- **Subtitle toggle** -- Show or hide subtitle overlays (for video content).
- **Reading music toggle** -- Enable or disable background music during playback.

### Text Track Visibility

Toggle which text tracks are visible using keyboard shortcuts or the control bar:

- **Original text** -- The source language sentence.
- **Transliteration** -- Phonetic rendering of the target language.
- **Translation** -- The translated sentence.

Each track can be shown or hidden independently.

### Sequence Mode

When both original and translation audio tracks are available and enabled, sequence mode activates automatically. In this mode:

1. The original language sentence plays first.
2. A brief dwell pause occurs.
3. The translation of the same sentence plays.
4. The player advances to the next sentence.

This creates an immersive language-learning experience where you hear each sentence in both languages before moving on.

### Word Highlighting

As audio plays, individual words are highlighted in real-time, synchronized to the narration. The active word is visually emphasized so you can follow along with the audio.

Click or tap any word in the text to **seek** to that word's position in the audio. Playback jumps to the exact timestamp where that word is spoken.

### Speed and Volume

- **Speed slider** -- Adjust playback speed for the translation audio (the up/down arrows on keyboard also control this).
- **Font size** -- Increase or decrease the text size using the +/- keys.

### Sentence and Chapter Navigation

- **Sentence jump** -- Type a sentence number to jump directly to that position.
- **Chapter dropdown** -- If the book has chapter markers, select a chapter from the dropdown to navigate there.

### Bookmarks

Save your position at any point:

- Click the bookmark button (or press the shortcut) to save the current position.
- Open the bookmark dropdown to see all saved bookmarks.
- Click a bookmark to jump back to that position.
- Remove bookmarks you no longer need.

### Resume

Your playback position is automatically saved to the server as you listen. When you return to the same book later (even from a different device or browser), playback resumes from where you left off.

### Keyboard Shortcuts (Web)

Press **H** at any time in the player to see the full shortcut help overlay. Here is the complete list:

**Playback and navigation:**

| Key | Action |
|-----|--------|
| Space | Play or pause the active track |
| Left / Right arrow | Previous or next chunk (keeps play state) |
| M | Toggle background music |
| F | Toggle fullscreen |
| R | Toggle image reel |
| Shift + Plus / Shift + Minus | Resize image reel |

**Text display:**

| Key | Action |
|-----|--------|
| O | Toggle original text line |
| Shift + O | Toggle original audio |
| Shift + P | Toggle translation audio |
| I | Toggle transliteration line |
| P | Toggle translation line |
| Plus / Minus | Increase or decrease font size |
| Up / Down arrow | Translation speed up or down |

**MyLinguist:**

| Key | Action |
|-----|--------|
| L | Toggle MyLinguist chat window |
| Ctrl + Plus / Ctrl + Minus | Increase or decrease MyLinguist font size |
| Alt + Left / Alt + Right | Previous or next word (stays on current lane) |
| Esc | Close the bubble |
| Enter or Space (on focused word) | Seek to that word |

**Fullscreen:**

| Key | Action |
|-----|--------|
| Shift + H | Show or hide advanced controls |

**Help:**

| Key | Action |
|-----|--------|
| H | Toggle the shortcut help overlay |
| Esc | Close dialogs and overlays |

---

## MyLinguist Dictionary

MyLinguist is an AI-powered dictionary assistant built into the interactive player. It provides instant word and phrase lookups without leaving the reading experience.

### Using MyLinguist

1. Click or tap any word in the original, transliteration, or translation text.
2. The MyLinguist bubble appears near the clicked word, showing a structured lookup result.

### Lookup Results

Each lookup returns structured information powered by a large language model:

- **Definition** -- The meaning of the word or phrase.
- **Part of speech** -- Noun, verb, adjective, etc.
- **Pronunciation** -- Phonetic rendering in brackets.
- **Etymology** -- Word origin and historical context.
- **Example sentence** -- A usage example with transliteration and translation when applicable.
- **Idioms** -- Related idiomatic expressions (for sentence-level lookups).
- **Related languages** -- The same word in other languages (e.g., how the Arabic word relates to similar words in Turkish, Persian, or Hindi).

### Controls

The MyLinguist bubble header provides:

- **Lookup language selector** -- Choose which language to explain the word in (defaults to the target language). A flag icon indicates the current selection.
- **LLM model selector** -- Choose which AI model to use for lookups (or leave on Auto).
- **Navigation arrows** -- Move to the previous or next word without closing the bubble. Use Alt + Left/Right as keyboard shortcuts.
- **TTS voice selector** -- Choose a voice for pronunciation.
- **Speak button** -- Hear the word pronounced aloud at normal speed.
- **Slow speak button** -- Hear the word pronounced at half speed.
- **Play from narration** -- If the word exists in the narrated audio, play it from the original recording.
- **Pin** -- Keep the bubble open even when clicking other words (otherwise it follows your clicks).
- **Dock/Float** -- Switch the bubble between a docked position at the bottom and a freely movable floating window.
- **Close** -- Dismiss the bubble.

Results are cached locally for instant re-lookup of previously queried words.

---

## Sentence Images and MyPainter

When a book is processed with image generation enabled, AI-generated illustrations appear for each sentence.

### Image Reel

The image reel is a horizontal scrolling strip of sentence illustrations displayed above the text panel. The currently active sentence's image is highlighted.

- **Toggle visibility** -- Press R or use the image reel toggle.
- **Resize** -- Press Shift + Plus or Shift + Minus to make the reel larger or smaller.
- **Navigate** -- Click any image thumbnail to jump to that sentence.
- **Fullscreen** -- Press F to view the current image in fullscreen.

### MyPainter

MyPainter lets you regenerate individual sentence images with custom prompts:

1. Click on a sentence image in the reel.
2. The MyPainter panel opens, showing the current image and its generation prompt.
3. Edit the prompt or adjust settings (style, dimensions, seed, steps).
4. Click regenerate to create a new image with your changes.
5. The new image replaces the previous one in the reel.

This is useful for fixing images that do not match the narrative or for experimenting with different visual styles for specific scenes.

---

## Subtitle Translation

The Subtitles tool translates subtitle files into other languages with narration.

### Source

The tool discovers subtitle files from the server's configured subtitle directory. Supported formats include SRT, VTT, SUB, and ASS.

Browse available subtitle files and select one to translate.

### Options

Configure the translation:

- **Source language** -- The language of the original subtitle file.
- **Target language** -- The language to translate into.
- **Translation provider** -- LLM or Google Translate.
- **Output format** -- Choose the output subtitle format.
- **Show original** -- Include the original text alongside translations.
- **Font size and emphasis** -- For ASS format output, control visual styling.

### Metadata

Attach TV show or film metadata to the subtitle job. This metadata appears in the library and helps organize translated subtitles.

### Processing

After configuring, submit the job. Progress appears in the Job Overview. When complete, the translated subtitle file can be downloaded or moved to the library.

---

## YouTube Video

The YouTube Video tool lets you download YouTube videos and their subtitle tracks to the NAS.

### Browsing

The page shows videos already downloaded to the NAS library. Each video displays its title, available subtitle tracks, and video formats.

### Downloading Subtitles

1. Select a video from the NAS library.
2. The system fetches available subtitle tracks from YouTube (manual and auto-generated).
3. Select the subtitle track and language you want.
4. Download the subtitle file to the NAS for later use with the Subtitles or Dub Video tools.

### Downloading Videos

Select a video format (resolution, fps) and download the video file to the NAS.

---

## Video Dubbing

The Dub Video tool generates dubbed audio tracks for videos, replacing the original language audio with a synthesized narration in another language.

### Source

Select a video from the NAS library and choose an associated subtitle file as the source for dubbing.

### Options

- **Target language** -- The language to dub into.
- **Translation provider** -- LLM or Google Translate.
- **Voice** -- Select the TTS voice for the dubbed audio.
- **Voice overrides** -- Set different voices per language.

### Metadata

Attach TV show or film metadata (title, season, episode).

### Tuning

Adjust technical parameters such as LLM model, translation batch size, and worker counts.

### Jobs

View the status of submitted dubbing jobs, monitor progress, and open completed dubs in the player.

---

## iOS and tvOS Apps

Native companion apps are available for iPhone, iPad, and Apple TV. They connect to the same ebook-tools server and provide the full interactive player experience.

### iOS (iPhone and iPad)

The iOS app provides:

- **Library browsing** -- Browse your processed books with cover art, organized by author, genre, or language.
- **Interactive player** -- The same word-level highlighting, audio track toggles, and sequence mode as the web interface, optimized for touch.
- **MyLinguist** -- Tap any word to look it up. The dictionary bubble adapts to the mobile layout.
- **Sentence images** -- View the image reel and browse illustrations with swipe gestures.
- **Offline playback** -- Content can be cached for offline listening.
- **Resume sync** -- Playback position syncs with the server, so you can switch between the web and iOS seamlessly.
- **Apple Music integration** -- Use Apple Music tracks as background reading music.

### tvOS (Apple TV)

The tvOS app is designed for the big screen with Siri Remote navigation:

- **Library browsing** -- Navigate the library using the Siri Remote's touch surface and click.
- **Playback** -- Full playback controls via the Siri Remote. Press Menu to go back.
- **Large text display** -- Optimized font sizes and layout for viewing from across the room.

### Signing In on Apple Devices

Both apps use the same credentials as the web interface. Enter your username and password on the login screen.

---

## Administration

The administration section is available only to users with the **admin** role. It is accessed from the sidebar under the Administration heading.

### User Management

Manage all user accounts in the system:

- **Create user** -- Add a new account with a username, password, and role. Available roles:
  - **Admin** -- Full access to all features including user management and system settings.
  - **Editor** -- Can create and manage processing jobs but cannot administer users or system settings.
  - **Viewer** -- Can browse the library and use the player but cannot submit new jobs.

- **Account status** -- Each account can be in one of three states:
  - **Active** -- Normal access.
  - **Suspended** -- Temporarily disabled. The user cannot sign in.
  - **Inactive** -- Deactivated account.

- **Actions** -- For each user, administrators can:
  - Reset their password.
  - Suspend or reactivate their account.
  - Update their profile (email, first name, last name).
  - Delete their account.

Administrators cannot delete or suspend their own account.

### Reading Music

Manage background music tracks that users can enable during playback:

- **Upload** -- Add new audio files (MP3, AAC, etc.) as background tracks. Give each track a descriptive label.
- **Set default** -- Choose which track plays by default when users enable reading music.
- **Rename** -- Update the label for any track.
- **Delete** -- Remove a track from the catalog.

### Settings

The Settings panel provides access to the full system configuration:

- **Configuration groups** -- Settings are organized into logical groups. Select a group to view and edit its values.
- **Validation** -- Validate changes before applying them to catch errors early.
- **Snapshots** -- Save the current configuration as a snapshot before making changes. Snapshots can be restored, exported, or deleted.
- **Import/Export** -- Transfer configuration between instances.

### System

Monitor and control the server:

- **System status** -- View server uptime, version, and resource usage.
- **Reload configuration** -- Apply configuration changes without restarting the server.
- **Restart server** -- Initiate a server restart with a countdown timer. The restart can be cancelled during the countdown.
- **Audit log** -- View a history of administrative actions performed on the system.

---

## Account Settings

Your account settings are accessible from the account panel at the bottom of the sidebar. Expand the panel by clicking your name.

### Change Password

1. Expand the account panel.
2. Click **Change password**.
3. Enter your current password and your new password.
4. Submit the form. A confirmation message appears on success.

### Theme

Select your preferred theme from the account panel. See [Theme and Appearance](#theme-and-appearance) for details.

### Sign Out

Click **Sign out** to end your session and return to the login screen.

---

## Troubleshooting

### Cannot sign in

- Verify that your username and password are correct. Passwords are case-sensitive.
- Your account may be suspended or inactive. Contact your administrator.
- If using OAuth (Google or Apple), ensure the provider is configured and your browser allows pop-ups.

### Library is empty

- If you have completed jobs that do not appear in the library, they may not have been moved to the library yet. Open the job in the Job Overview and use the **Move to library** action.
- Try the **Reindex library** button in the library toolbar.

### Player does not start

- Ensure the job has finished processing at least one chunk. The progress indicator in the Job Overview shows how many sentences are playable.
- Check that your browser allows audio autoplay. Some browsers block autoplay until you interact with the page.

### Audio is not playing

- Verify that at least one audio track toggle (original or translation) is enabled in the player navigation bar.
- Check your browser's volume and ensure the tab is not muted.
- If using sequence mode, both audio tracks must be available. If one track failed to generate, sequence mode will not activate.

### Word highlighting is out of sync

- Try adjusting the playback speed. Some TTS voices have slight timing variations.
- Navigate to the next chunk and back to reset the audio synchronization.

### Images are not showing

- Images must be enabled when the book is processed. If the job was submitted without image generation, no images will be available.
- Press R to toggle the image reel visibility. It may be hidden.
- If images are still generating, a progress indicator appears in the Job Overview showing the image generation percentage.

### Job is stuck or failed

- Check the job's progress card for error messages.
- Try pausing and resuming the job.
- If the job failed, you can restart it or copy its settings to a new job.
- For persistent failures, check that the backend server is running and the required external services (TTS, translation, image generation) are accessible.

### iOS or tvOS app cannot connect

- Ensure the app is configured to point to the correct server URL.
- Verify that the server is reachable from the device's network.
- Check that your credentials are correct and your account is active.

### Changes to settings are not taking effect

- After changing server settings in the Administration panel, use **Reload configuration** in the System panel to apply changes without restarting.
- If configuration changes still do not apply, a full server restart may be required.
