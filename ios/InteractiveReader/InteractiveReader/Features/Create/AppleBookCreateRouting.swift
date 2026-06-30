import Foundation

extension AppleBookCreatePresentation {
    static func availableCreateModes(isTV: Bool) -> [AppleCreateMode] {
        AppleCreateMode.allCases
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

    static func webCreateHandoffURL(
        apiBaseURL: URL?,
        mode: AppleCreateMode,
        templateID: String? = nil
    ) -> URL? {
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
        var queryItems = [
            URLQueryItem(name: "view", value: webCreateViewID(for: mode)),
            URLQueryItem(name: "source", value: "apple")
        ]
        if let templateID = templateID?.trimmingCharacters(in: .whitespacesAndNewlines),
           !templateID.isEmpty {
            queryItems.append(URLQueryItem(name: "template_id", value: templateID))
        }
        components.queryItems = queryItems
        components.fragment = nil
        return components.url
    }
}
