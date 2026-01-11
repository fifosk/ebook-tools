# Interactive Reader (iOS, iPadOS, tvOS)

A SwiftUI app that authenticates against the ebook-tools FastAPI backend, lists Library entries, and plays book, subtitle, and video items with an interactive reader experience similar to the web client. Library playback relies on `/api/library/media/{job_id}` plus `/api/jobs/{job_id}/timing`, and uses the same access-token query pattern as the web player for media URLs.

## Requirements

- Xcode 15.0+ (iOS 17 SDK) with Swift Concurrency support.
- An accessible ebook-tools API (defaults to `https://api.langtools.fifosk.synology.me` on both iOS/iPadOS and tvOS).
- Library files exposed through `/api/library/media/{job_id}` (the app appends `access_token` for media streaming).

## Project layout

```
ios/InteractiveReader
├── InteractiveReader.xcodeproj
├── InteractiveReader/        # Swift sources & resources
│   ├── App/                  # Entry point
│   ├── Features/             # UI flows (auth, library, playback)
│   ├── Models/               # Codable contracts shared with the backend
│   ├── Services/             # API + audio playback helpers
│   ├── Utilities/            # Cross-cutting helpers (storage resolver, string utils)
│   └── Resources/            # Assets + Info.plist
```

## Running the app

1. Open `ios/InteractiveReader/InteractiveReader.xcodeproj` in Xcode.
2. Select the `InteractiveReader` (iOS/iPadOS) or `InteractiveReaderTV` (tvOS) scheme and a target device.
3. Run (`⌘R`).
4. In the UI, set the API base URL (defaults to `https://api.langtools.fifosk.synology.me`), sign in, and open a Library item.

### Library media URLs

The client streams library files from `/api/library/media/{job_id}/file/...` and appends the `access_token` query parameter so AVPlayer can fetch protected media without custom headers. Ensure the API host is reachable from your device (LAN IP or Bonjour hostname).

### Authentication

The app uses `/api/auth/login` and stores the bearer token locally. Media URLs append `access_token` in the query string for streaming.

## Limitations / TODOs

- Live-updating jobs (`/media/live`) are not wired yet—load completed jobs only.
- Only the translation track is rendered; original-language timelines can be added once the API exposes both tracks concurrently.
- Chunk auto-scroll + background refresh subscriptions can be layered on using the existing `AudioPlayerCoordinator` hooks.
