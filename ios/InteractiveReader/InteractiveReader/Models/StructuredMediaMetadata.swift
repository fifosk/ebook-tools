// StructuredMediaMetadata.swift
// Typed Codable structs for structured media metadata (v2).
// Mirrors the backend Pydantic models in
// modules/services/metadata/structured_schema.py

import Foundation

// MARK: - Nested sub-types

struct MetadataSourceIds: Codable {
    var isbn: String?
    var isbn13: String?
    var openlibrary: String?
    var openlibraryBook: String?
    var googleBooks: String?
    var tmdb: Int?
    var imdb: String?
    var tvmazeShow: Int?
    var tvmazeEpisode: Int?
    var wikidata: String?
    var youtubeVideo: String?
    var youtubeChannel: String?
}

struct MetadataSeriesInfo: Codable {
    var seriesTitle: String?
    var season: Int?
    var episode: Int?
    var episodeTitle: String?
    var seriesId: String?
    var episodeId: String?
}

struct MetadataYouTubeInfo: Codable {
    var videoId: String?
    var channelId: String?
    var channelName: String?
    var uploadDate: String?
}

// MARK: - Main sections

struct MetadataSource: Codable {
    var title: String?
    var author: String?
    var year: Int?
    var summary: String?
    var genres: [String]?
    var language: String?
    var isbn: String?
    var isbn13: String?
    var series: MetadataSeriesInfo?
    var youtube: MetadataYouTubeInfo?
    var runtimeMinutes: Int?
    var rating: Double?
    var votes: Int?
}

struct MetadataLanguageConfig: Codable {
    var inputLanguage: String?
    var originalLanguage: String?
    var targetLanguage: String?
    var targetLanguages: [String]?
    var translationProvider: String?
    var translationModel: String?
    var translationModelRequested: String?
    var transliterationMode: String?
    var transliterationModel: String?
    var transliterationModule: String?
}

struct MetadataContentStructure: Codable {
    var totalSentences: Int?
    var contentIndexPath: String?
    var contentIndexUrl: String?
    var contentIndexSummary: MetadataContentIndexSummary?
}

struct MetadataContentIndexSummary: Codable {
    var chapterCount: Int?
    var alignment: String?
}

struct MetadataCoverAssets: Codable {
    var coverFile: String?
    var coverUrl: String?
    var bookCoverUrl: String?
    var jobCoverAsset: String?
    var jobCoverAssetUrl: String?
}

struct MetadataEnrichmentProvenance: Codable {
    var source: String?
    var confidence: String?
    var queriedAt: String?
    var sourceIds: MetadataSourceIds?
    // lookupResult is generic JSON — decode as [String: JSONValue]
}

// MARK: - Top-level container

struct StructuredMediaMetadata: Codable {
    var metadataVersion: Int
    var mediaType: String
    var source: MetadataSource
    var languageConfig: MetadataLanguageConfig?
    var contentStructure: MetadataContentStructure?
    var coverAssets: MetadataCoverAssets?
    var enrichment: MetadataEnrichmentProvenance?
    var jobLabel: String?

    /// Try to decode from a generic JSON dictionary.
    /// Returns nil if the dictionary doesn't contain a valid structured metadata payload.
    static func from(json: [String: JSONValue]) -> StructuredMediaMetadata? {
        guard let versionValue = json["metadataVersion"]?.intValue,
              versionValue >= 2 else {
            return nil
        }
        // Re-encode to JSON data and decode via Codable
        guard let data = try? JSONSerialization.data(
            withJSONObject: jsonValueToAny(json),
            options: []
        ) else {
            return nil
        }
        let decoder = JSONDecoder()
        return try? decoder.decode(StructuredMediaMetadata.self, from: data)
    }

    /// Convert JSONValue dictionary to Foundation types for JSONSerialization.
    private static func jsonValueToAny(_ dict: [String: JSONValue]) -> [String: Any] {
        var result: [String: Any] = [:]
        for (key, value) in dict {
            result[key] = jsonValueElementToAny(value)
        }
        return result
    }

    private static func jsonValueElementToAny(_ value: JSONValue) -> Any {
        switch value {
        case .string(let s): return s
        case .number(let n): return n
        case .bool(let b): return b
        case .null: return NSNull()
        case .object(let dict): return jsonValueToAny(dict)
        case .array(let arr): return arr.map { jsonValueElementToAny($0) }
        }
    }
}
