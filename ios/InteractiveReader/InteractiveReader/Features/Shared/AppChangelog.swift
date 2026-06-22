struct AppChangelogEntry: Identifiable, Equatable {
    let id: String
    let title: String
    let detail: String
}

struct AppChangelogDay: Identifiable, Equatable {
    let id: String
    let dateLabel: String
    let version: String
    let entries: [AppChangelogEntry]
}

enum AppChangelog {
    static let days: [AppChangelogDay] = AppChangelogData.days
}
