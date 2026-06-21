import Foundation
import Security

final class SessionTokenStore {
    static let shared = SessionTokenStore()

    private let service = "com.fifosk.ebooktools.InteractiveReader.session"
    private let account = "authToken"
    private let legacyDefaultsKey = "authToken"
    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    func loadToken() -> String? {
        if let token = readKeychainToken()?.nonEmptyValue {
            return token
        }

        guard let legacyToken = defaults.string(forKey: legacyDefaultsKey)?.nonEmptyValue else {
            return nil
        }
        saveToken(legacyToken)
        defaults.removeObject(forKey: legacyDefaultsKey)
        return legacyToken
    }

    func saveToken(_ token: String?) {
        guard let token = token?.nonEmptyValue,
              let data = token.data(using: .utf8) else {
            deleteToken()
            return
        }

        let attributes: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]

        let updates: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]

        let status = SecItemUpdate(attributes as CFDictionary, updates as CFDictionary)
        if status == errSecSuccess {
            defaults.removeObject(forKey: legacyDefaultsKey)
            return
        }

        var insert = attributes
        insert[kSecValueData as String] = data
        insert[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        if SecItemAdd(insert as CFDictionary, nil) == errSecSuccess {
            defaults.removeObject(forKey: legacyDefaultsKey)
        }
    }

    func deleteToken() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)
        defaults.removeObject(forKey: legacyDefaultsKey)
    }

    private func readKeychainToken() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }
}
