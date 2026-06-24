import Foundation

extension AppleBookCreatePresentation {
    static func availableCreateModes(isTV: Bool) -> [AppleCreateMode] {
        isTV ? [.generatedBook] : AppleCreateMode.allCases
    }

    static func webCreateViewID(for mode: AppleCreateMode) -> String {
        switch mode {
        case .generatedBook:
            return "books:create"
        case .narrateEbook:
            return "pipeline:source"
        case .subtitleJob:
            return "subtitles:home"
        case .youtubeDub:
            return "subtitles:youtube-dub"
        }
    }

    static func webCreateHandoffURL(apiBaseURL: URL?, mode: AppleCreateMode) -> URL? {
        guard
            let apiBaseURL,
            var components = URLComponents(url: apiBaseURL, resolvingAgainstBaseURL: false),
            let scheme = components.scheme,
            !scheme.isEmpty,
            var host = components.host,
            !host.isEmpty
        else {
            return nil
        }

        if host.hasPrefix("api.") {
            host.removeFirst(4)
        }

        if (host == "localhost" || host == "127.0.0.1" || host == "::1"), components.port == 8000 {
            components.port = 5173
        }

        components.host = host
        components.path = "/"
        components.queryItems = [
            URLQueryItem(name: "view", value: webCreateViewID(for: mode))
        ]
        components.fragment = nil
        return components.url
    }
}
