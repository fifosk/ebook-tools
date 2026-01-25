import Foundation

extension JSONValue {
    var objectValue: [String: JSONValue]? {
        if case let .object(value) = self {
            return value
        }
        return nil
    }

    var arrayValue: [JSONValue]? {
        if case let .array(value) = self {
            return value
        }
        return nil
    }

    var stringValue: String? {
        switch self {
        case let .string(value):
            return value.nonEmptyValue
        case let .number(value):
            guard value.isFinite else { return nil }
            return String(value).nonEmptyValue
        case let .bool(value):
            return value ? "true" : "false"
        case let .array(values):
            for value in values {
                if let string = value.stringValue {
                    return string
                }
            }
            return nil
        default:
            return nil
        }
    }

    var intValue: Int? {
        switch self {
        case let .number(value):
            guard value.isFinite else { return nil }
            return Int(value)
        case let .string(value):
            return Int(value)
        case let .bool(value):
            return value ? 1 : 0
        case let .array(values):
            for value in values {
                if let intValue = value.intValue {
                    return intValue
                }
            }
            return nil
        default:
            return nil
        }
    }
}
