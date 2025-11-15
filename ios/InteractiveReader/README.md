# Interactive Reader (iOS)

A SwiftUI prototype that talks to the ebook-tools FastAPI backend and reproduces the interactive reader experience from the web client. The app lets you enter a job ID, resolves the same `/api/pipelines/jobs/{job_id}/media` and `/api/jobs/{job_id}/timing` endpoints, and presents chunk-level playback with synchronized translated text highlighting.

## Requirements

- Xcode 15.0+ (iOS 17 SDK) with Swift Concurrency support.
- An accessible ebook-tools API (defaults to `http://localhost:8000`).
- Storage files exposed through `http://<api>/storage/jobs/<job_id>/…` or a custom `VITE_STORAGE_BASE_URL` equivalent.

## Project layout

```
ios/InteractiveReader
├── InteractiveReader.xcodeproj
├── InteractiveReader/        # Swift sources & resources
│   ├── App/                  # Entry point
│   ├── Features/             # UI flows (job loader + interactive player)
│   ├── Models/               # Codable contracts shared with the backend
│   ├── Services/             # API + audio playback helpers
│   ├── Utilities/            # Cross-cutting helpers (storage resolver, string utils)
│   └── Resources/            # Assets + Info.plist
```

## Running the app

1. Open `ios/InteractiveReader/InteractiveReader.xcodeproj` in Xcode.
2. Select the `InteractiveReader` scheme and an iOS Simulator (or device) target.
3. Run (`⌘R`).
4. In the UI, set the API base URL (defaults to `http://localhost:8000`) plus any auth headers, enter a `job_id`, and tap **Load job**.

### Storage URLs

The client mimics the web resolver logic:
- If a custom storage base URL is supplied, it is used verbatim.
- Otherwise the app appends `/storage/jobs` to the API base host.

Make sure the API host allows the iOS client (simulator/device) to reach both the API routes and `storage/jobs` assets—if necessary, expose the server via LAN or replace `localhost` with your machine IP.

### Authentication

Provide the same bearer token (`Authorization`), `X-User-Id`, and `X-User-Role` header values as the web client when connecting to secured environments.

## Limitations / TODOs

- Live-updating jobs (`/media/live`) are not wired yet—load completed jobs only.
- Only the translation track is rendered; original-language timelines can be added once the API exposes both tracks concurrently.
- Chunk auto-scroll + background refresh subscriptions can be layered on using the existing `AudioPlayerCoordinator` hooks.
