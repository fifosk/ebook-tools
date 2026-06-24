import Foundation

enum AppleBookCreateMetadataJSON {
    static func prettyString(from metadata: [String: JSONValue]?) -> String {
        guard let metadata, !metadata.isEmpty else {
            return ""
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        guard let data = try? encoder.encode(metadata) else {
            return ""
        }
        return String(data: data, encoding: .utf8) ?? ""
    }

    static func parseObject(_ value: String) -> (metadata: [String: JSONValue]?, error: String?) {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return (nil, nil)
        }
        guard let data = trimmed.data(using: .utf8) else {
            return (nil, "Metadata JSON must be valid UTF-8 text.")
        }
        do {
            return (try JSONDecoder().decode([String: JSONValue].self, from: data), nil)
        } catch {
            return (nil, "Enter a valid JSON object.")
        }
    }

    static func cacheClearMessage(cleared: Int, kind: String, query: String) -> String {
        let entryLabel = cleared == 1 ? "entry" : "entries"
        return "Cleared \(cleared) cached \(kind) metadata \(entryLabel) for \(query)."
    }

    static func updateNestedText(
        in sectionDraft: inout [String: JSONValue],
        nestedKey: String,
        key: String,
        value: String
    ) {
        var nested = sectionDraft[nestedKey]?.objectValue ?? [:]
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmedValue.isEmpty {
            nested.removeValue(forKey: key)
        } else {
            nested[key] = .string(trimmedValue)
        }
        if nested.isEmpty {
            sectionDraft.removeValue(forKey: nestedKey)
        } else {
            sectionDraft[nestedKey] = .object(nested)
        }
    }
}
