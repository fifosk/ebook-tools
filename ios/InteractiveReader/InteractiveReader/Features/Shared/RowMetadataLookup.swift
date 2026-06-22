enum RowMetadataLookup {
    static func metadataString(
        in sources: [[String: JSONValue]],
        keys: [String],
        maxDepth: Int = 4
    ) -> String? {
        for source in sources {
            if let found = metadataString(in: source, keys: keys, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    static func metadataString(
        in metadata: [String: JSONValue],
        keys: [String],
        maxDepth: Int = 4
    ) -> String? {
        for key in keys {
            if let found = metadataString(in: metadata, key: key, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    static func metadataValue(
        in sources: [[String: JSONValue]],
        keys: [String],
        maxDepth: Int = 4
    ) -> JSONValue? {
        for source in sources {
            if let found = metadataValue(in: source, keys: keys, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    static func metadataValue(
        in metadata: [String: JSONValue],
        keys: [String],
        maxDepth: Int = 4
    ) -> JSONValue? {
        for key in keys {
            if let found = metadataValue(in: metadata, key: key, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    static func firstObject(
        in sources: [[String: JSONValue]],
        paths: [[String]]
    ) -> [String: JSONValue]? {
        for source in sources {
            if let found = firstObject(in: source, paths: paths) {
                return found
            }
        }
        return nil
    }

    static func firstObject(
        in metadata: [String: JSONValue],
        paths: [[String]]
    ) -> [String: JSONValue]? {
        for path in paths {
            if let value = nestedValue(metadata, path: path)?.objectValue {
                return value
            }
        }
        return nil
    }

    static func nestedValue(_ source: [String: JSONValue], path: [String]) -> JSONValue? {
        var current: JSONValue = .object(source)
        for key in path {
            guard let object = current.objectValue, let next = object[key] else { return nil }
            current = next
        }
        return current
    }

    private static func metadataString(
        in metadata: [String: JSONValue],
        key: String,
        maxDepth: Int
    ) -> String? {
        if let value = metadata[key]?.stringValue {
            return value
        }
        guard maxDepth > 0 else { return nil }
        for value in metadata.values {
            if let nested = value.objectValue {
                if let found = metadataString(in: nested, key: key, maxDepth: maxDepth - 1) {
                    return found
                }
            }
            if case let .array(items) = value {
                for entry in items {
                    if let nested = entry.objectValue,
                       let found = metadataString(in: nested, key: key, maxDepth: maxDepth - 1) {
                        return found
                    }
                }
            }
        }
        return nil
    }

    private static func metadataValue(
        in metadata: [String: JSONValue],
        key: String,
        maxDepth: Int
    ) -> JSONValue? {
        if let value = metadata[key] {
            return value
        }
        guard maxDepth > 0 else { return nil }
        for value in metadata.values {
            if let nested = value.objectValue {
                if let found = metadataValue(in: nested, key: key, maxDepth: maxDepth - 1) {
                    return found
                }
            }
            if case let .array(items) = value {
                for entry in items {
                    if let nested = entry.objectValue,
                       let found = metadataValue(in: nested, key: key, maxDepth: maxDepth - 1) {
                        return found
                    }
                }
            }
        }
        return nil
    }
}
