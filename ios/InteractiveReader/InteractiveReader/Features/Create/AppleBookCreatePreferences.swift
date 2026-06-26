import Foundation

struct AppleBookCreatePreferenceScope {
    let baseKey: String
    let youtubeBaseDir: String

    var youtubeLibraryLoadKey: String {
        AppleBookCreateStorageKeys.youtubeLibraryLoad(
            baseKey: baseKey,
            baseDir: youtubeBaseDir
        )
    }

    func storedYoutubeSelectionPath(field: String, defaults: UserDefaults = .standard) -> String? {
        AppleBookCreatePreferences.storedYoutubeSelectionPath(
            baseKey: baseKey,
            baseDir: youtubeBaseDir,
            field: field,
            defaults: defaults
        )
    }

    func persistYoutubeSelectionPath(
        _ path: String,
        field: String,
        defaults: UserDefaults = .standard
    ) {
        AppleBookCreatePreferences.persistYoutubeSelectionPath(
            path,
            baseKey: baseKey,
            baseDir: youtubeBaseDir,
            field: field,
            defaults: defaults
        )
    }

    func storedYoutubeBaseDir(defaults: UserDefaults = .standard) -> String? {
        AppleBookCreatePreferences.storedYoutubeBaseDir(baseKey: baseKey, defaults: defaults)
    }

    func persistYoutubeBaseDir(_ baseDir: String, defaults: UserDefaults = .standard) {
        AppleBookCreatePreferences.persistYoutubeBaseDir(baseDir, baseKey: baseKey, defaults: defaults)
    }

    func storedSubtitleShowOriginal(defaults: UserDefaults = .standard) -> Bool? {
        AppleBookCreatePreferences.storedSubtitleShowOriginal(baseKey: baseKey, defaults: defaults)
    }

    func persistSubtitleShowOriginal(_ value: Bool, defaults: UserDefaults = .standard) {
        AppleBookCreatePreferences.persistSubtitleShowOriginal(value, baseKey: baseKey, defaults: defaults)
    }

    func storedLanguagePreferences(
        defaults: UserDefaults = .standard,
        decoder: JSONDecoder = JSONDecoder()
    ) -> AppleCreateLanguagePreferences? {
        AppleBookCreatePreferences.storedLanguagePreferences(
            baseKey: baseKey,
            defaults: defaults,
            decoder: decoder
        )
    }

    func persistLanguagePreferences(
        _ preferences: AppleCreateLanguagePreferences,
        defaults: UserDefaults = .standard,
        encoder: JSONEncoder = JSONEncoder()
    ) {
        AppleBookCreatePreferences.persistLanguagePreferences(
            preferences,
            baseKey: baseKey,
            defaults: defaults,
            encoder: encoder
        )
    }
}

enum AppleBookCreatePreferences {
    static func storedYoutubeSelectionPath(
        baseKey: String,
        baseDir: String,
        field: String,
        defaults: UserDefaults = .standard
    ) -> String? {
        defaults.string(
            forKey: AppleBookCreateStorageKeys.youtubeSelection(
                baseKey: baseKey,
                baseDir: baseDir,
                field: field
            )
        )?.nonEmptyValue
    }

    static func persistYoutubeSelectionPath(
        _ path: String,
        baseKey: String,
        baseDir: String,
        field: String,
        defaults: UserDefaults = .standard
    ) {
        setOrRemove(
            path,
            forKey: AppleBookCreateStorageKeys.youtubeSelection(
                baseKey: baseKey,
                baseDir: baseDir,
                field: field
            ),
            defaults: defaults
        )
    }

    static func storedYoutubeBaseDir(
        baseKey: String,
        defaults: UserDefaults = .standard
    ) -> String? {
        defaults.string(forKey: AppleBookCreateStorageKeys.youtubeBaseDir(baseKey: baseKey))?.nonEmptyValue
    }

    static func persistYoutubeBaseDir(
        _ baseDir: String,
        baseKey: String,
        defaults: UserDefaults = .standard
    ) {
        setOrRemove(
            baseDir,
            forKey: AppleBookCreateStorageKeys.youtubeBaseDir(baseKey: baseKey),
            defaults: defaults
        )
    }

    static func storedSubtitleShowOriginal(
        baseKey: String,
        defaults: UserDefaults = .standard
    ) -> Bool? {
        let key = AppleBookCreateStorageKeys.subtitleShowOriginal(baseKey: baseKey)
        guard defaults.object(forKey: key) != nil else {
            return nil
        }
        return defaults.bool(forKey: key)
    }

    static func persistSubtitleShowOriginal(
        _ value: Bool,
        baseKey: String,
        defaults: UserDefaults = .standard
    ) {
        defaults.set(value, forKey: AppleBookCreateStorageKeys.subtitleShowOriginal(baseKey: baseKey))
    }

    static func storedLanguagePreferences(
        baseKey: String,
        defaults: UserDefaults = .standard,
        decoder: JSONDecoder = JSONDecoder()
    ) -> AppleCreateLanguagePreferences? {
        guard let data = defaults.data(forKey: AppleBookCreateStorageKeys.languagePreferences(baseKey: baseKey)) else {
            return nil
        }
        return try? decoder.decode(AppleCreateLanguagePreferences.self, from: data)
    }

    static func persistLanguagePreferences(
        _ preferences: AppleCreateLanguagePreferences,
        baseKey: String,
        defaults: UserDefaults = .standard,
        encoder: JSONEncoder = JSONEncoder()
    ) {
        guard let data = try? encoder.encode(preferences) else {
            return
        }
        defaults.set(data, forKey: AppleBookCreateStorageKeys.languagePreferences(baseKey: baseKey))
    }

    private static func setOrRemove(_ value: String, forKey key: String, defaults: UserDefaults) {
        if let value = value.nonEmptyValue {
            defaults.set(value, forKey: key)
        } else {
            defaults.removeObject(forKey: key)
        }
    }
}
