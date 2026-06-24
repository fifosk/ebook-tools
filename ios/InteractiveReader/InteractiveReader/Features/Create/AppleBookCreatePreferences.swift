import Foundation

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

    private static func setOrRemove(_ value: String, forKey key: String, defaults: UserDefaults) {
        if let value = value.nonEmptyValue {
            defaults.set(value, forKey: key)
        } else {
            defaults.removeObject(forKey: key)
        }
    }
}
