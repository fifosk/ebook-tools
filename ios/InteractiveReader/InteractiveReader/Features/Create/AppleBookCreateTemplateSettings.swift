import Foundation

enum AppleBookCreateTemplateSettings {
    static func mode(for template: CreationTemplateEntry) -> AppleCreateMode? {
        switch template.normalizedMode {
        case "generated_book":
            return .generatedBook
        case "narrate_ebook":
            return .narrateEbook
        case "subtitle_job":
            return .subtitleJob
        case "youtube_dub":
            return .youtubeDub
        default:
            return nil
        }
    }

    static func compatibleTemplates(
        from templates: [CreationTemplateEntry],
        for mode: AppleCreateMode
    ) -> [CreationTemplateEntry] {
        templates.filter { template in
            self.mode(for: template) == mode
        }
    }

    static func metadataObject(from formState: [String: JSONValue]) -> [String: JSONValue]? {
        object(from: formState["media_metadata"])
            ?? object(from: formState["media_metadata_json"])
            ?? object(from: formState["youtube_metadata"])
    }

    static func formState(from template: CreationTemplateEntry) -> [String: JSONValue]? {
        template.payload["form_state"]?.objectValue
            ?? template.payload["formState"]?.objectValue
            ?? template.payload["payload"]?.objectValue?["form_state"]?.objectValue
    }

    static func settings(from template: CreationTemplateEntry) -> [String: JSONValue]? {
        formState(from: template) ?? template.payload
    }

    static func discoveryState(from template: CreationTemplateEntry) -> [String: JSONValue]? {
        object(from: template.payload["discovery_state"])
            ?? object(from: template.payload["discoveryState"])
            ?? object(from: template.payload["payload"]?.objectValue?["discovery_state"])
            ?? object(from: template.payload["payload"]?.objectValue?["discoveryState"])
    }

    static func object(from value: JSONValue?) -> [String: JSONValue]? {
        guard let value else { return nil }
        if let object = value.objectValue {
            return object
        }
        guard case let .string(text) = value,
              let data = text.data(using: .utf8),
              let object = try? JSONDecoder().decode([String: JSONValue].self, from: data) else {
            return nil
        }
        return object
    }

    static func stringDictionary(from value: JSONValue?) -> [String: String]? {
        guard let object = object(from: value) else {
            return nil
        }
        return object.reduce(into: [String: String]()) { result, element in
            if let value = element.value.stringValue {
                result[element.key] = value
            }
        }
    }

    static func string(_ object: [String: JSONValue], _ key: String) -> String? {
        object[key]?.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue
    }

    static func stringArray(_ object: [String: JSONValue], _ key: String) -> [String] {
        guard let value = object[key] else { return [] }
        if let array = value.arrayValue {
            return array.compactMap { $0.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue }
        }
        return value.stringValue?
            .split(separator: ",")
            .compactMap { String($0).trimmingCharacters(in: .whitespacesAndNewlines).nonEmptyValue } ?? []
    }

    static func int(_ object: [String: JSONValue], _ key: String) -> Int? {
        object[key]?.intValue
    }

    static func double(_ object: [String: JSONValue], _ key: String) -> Double? {
        switch object[key] {
        case let .number(value):
            return value.isFinite ? value : nil
        case let .string(value):
            return Double(value.trimmingCharacters(in: .whitespacesAndNewlines))
        case let .bool(value):
            return value ? 1 : 0
        default:
            return nil
        }
    }

    static func bool(_ object: [String: JSONValue], _ key: String) -> Bool? {
        switch object[key] {
        case let .bool(value):
            return value
        case let .number(value):
            return value != 0
        case let .string(value):
            switch value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
            case "1", "true", "yes", "on":
                return true
            case "0", "false", "no", "off":
                return false
            default:
                return nil
            }
        default:
            return nil
        }
    }

    static func endSentenceText(from value: JSONValue?) -> String? {
        switch value {
        case .null, nil:
            return ""
        default:
            return value?.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        }
    }
}
