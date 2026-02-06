import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Structured Linguist Content View

#if os(iOS)
/// View that renders a parsed LinguistLookupResult with proper formatting
struct StructuredLinguistContentView: View {
    let result: LinguistLookupResult
    let font: Font
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Definition (always shown)
            TappableWordText(text: result.definition, font: font, color: color)

            // Part of speech & pronunciation
            if let pos = result.partOfSpeech, !pos.isEmpty {
                HStack(spacing: 4) {
                    Text("•")
                        .font(font)
                        .foregroundStyle(color.opacity(0.6))
                    Text(pos)
                        .font(font)
                        .italic()
                        .foregroundStyle(color.opacity(0.8))
                    if let pron = result.pronunciation, !pron.isEmpty {
                        Text("[\(pron)]")
                            .font(font)
                            .foregroundStyle(color.opacity(0.7))
                    }
                }
            } else if let pron = result.pronunciation, !pron.isEmpty {
                HStack(spacing: 4) {
                    Text("•")
                        .font(font)
                        .foregroundStyle(color.opacity(0.6))
                    Text("[\(pron)]")
                        .font(font)
                        .foregroundStyle(color.opacity(0.7))
                }
            }

            // Etymology
            if let etymology = result.etymology, !etymology.isEmpty {
                HStack(alignment: .top, spacing: 4) {
                    Text("⟶")
                        .font(font)
                        .foregroundStyle(color.opacity(0.5))
                    TappableWordText(text: etymology, font: font, color: color.opacity(0.85))
                }
            }

            // Example
            if let example = result.example, !example.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .top, spacing: 4) {
                        Text("„")
                            .font(font)
                            .foregroundStyle(color.opacity(0.5))
                        VStack(alignment: .leading, spacing: 2) {
                            TappableWordText(text: example, font: font.italic(), color: color.opacity(0.85))
                            if let translit = result.exampleTransliteration, !translit.isEmpty {
                                Text("(\(translit))")
                                    .font(font)
                                    .foregroundStyle(color.opacity(0.6))
                            }
                        }
                    }
                    if let translation = result.exampleTranslation, !translation.isEmpty {
                        HStack(alignment: .top, spacing: 4) {
                            Text("→")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            TappableWordText(text: translation, font: font, color: color.opacity(0.75))
                        }
                    }
                }
            }

            // Idioms (for sentences)
            if let idioms = result.idioms, !idioms.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Idioms:")
                        .font(font)
                        .fontWeight(.medium)
                        .foregroundStyle(color.opacity(0.7))
                    ForEach(idioms, id: \.self) { idiom in
                        HStack(alignment: .top, spacing: 4) {
                            Text("•")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            TappableWordText(text: idiom, font: font, color: color.opacity(0.9))
                        }
                    }
                }
            }

            // Related languages
            if let related = result.relatedLanguages, !related.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Related:")
                        .font(font)
                        .fontWeight(.medium)
                        .foregroundStyle(color.opacity(0.7))
                    ForEach(related) { lang in
                        HStack(spacing: 4) {
                            Text("•")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            Text(lang.language + ":")
                                .font(font)
                                .foregroundStyle(color.opacity(0.7))
                            Text(lang.word)
                                .font(font)
                                .foregroundStyle(color)
                                .contextMenu {
                                    let sanitized = TextLookupSanitizer.sanitize(lang.word)
                                    Button("Look Up") {
                                        DictionaryLookupPresenter.show(term: sanitized)
                                    }
                                    Button("Copy") {
                                        UIPasteboard.general.string = sanitized
                                    }
                                }
                            if let trans = lang.transliteration, !trans.isEmpty {
                                Text("(\(trans))")
                                    .font(font)
                                    .foregroundStyle(color.opacity(0.7))
                            }
                        }
                    }
                }
            }
        }
    }
}
#endif

#if os(tvOS)
/// tvOS version of structured content view (no tappable words or context menus)
struct StructuredLinguistContentView: View {
    let result: LinguistLookupResult
    let font: Font
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Definition (always shown)
            Text(result.definition)
                .font(font)
                .foregroundStyle(color)

            // Part of speech & pronunciation
            if let pos = result.partOfSpeech, !pos.isEmpty {
                HStack(spacing: 4) {
                    Text("•")
                        .font(font)
                        .foregroundStyle(color.opacity(0.6))
                    Text(pos)
                        .font(font)
                        .italic()
                        .foregroundStyle(color.opacity(0.8))
                    if let pron = result.pronunciation, !pron.isEmpty {
                        Text("[\(pron)]")
                            .font(font)
                            .foregroundStyle(color.opacity(0.7))
                    }
                }
            } else if let pron = result.pronunciation, !pron.isEmpty {
                HStack(spacing: 4) {
                    Text("•")
                        .font(font)
                        .foregroundStyle(color.opacity(0.6))
                    Text("[\(pron)]")
                        .font(font)
                        .foregroundStyle(color.opacity(0.7))
                }
            }

            // Etymology
            if let etymology = result.etymology, !etymology.isEmpty {
                HStack(alignment: .top, spacing: 4) {
                    Text("⟶")
                        .font(font)
                        .foregroundStyle(color.opacity(0.5))
                    Text(etymology)
                        .font(font)
                        .foregroundStyle(color.opacity(0.85))
                }
            }

            // Example
            if let example = result.example, !example.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .top, spacing: 4) {
                        Text("„")
                            .font(font)
                            .foregroundStyle(color.opacity(0.5))
                        VStack(alignment: .leading, spacing: 2) {
                            Text(example)
                                .font(font.italic())
                                .foregroundStyle(color.opacity(0.85))
                            if let translit = result.exampleTransliteration, !translit.isEmpty {
                                Text("(\(translit))")
                                    .font(font)
                                    .foregroundStyle(color.opacity(0.6))
                            }
                        }
                    }
                    if let translation = result.exampleTranslation, !translation.isEmpty {
                        HStack(alignment: .top, spacing: 4) {
                            Text("→")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            Text(translation)
                                .font(font)
                                .foregroundStyle(color.opacity(0.75))
                        }
                    }
                }
            }

            // Idioms (for sentences)
            if let idioms = result.idioms, !idioms.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Idioms:")
                        .font(font)
                        .fontWeight(.medium)
                        .foregroundStyle(color.opacity(0.7))
                    ForEach(idioms, id: \.self) { idiom in
                        HStack(alignment: .top, spacing: 4) {
                            Text("•")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            Text(idiom)
                                .font(font)
                                .foregroundStyle(color.opacity(0.9))
                        }
                    }
                }
            }

            // Related languages
            if let related = result.relatedLanguages, !related.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Related:")
                        .font(font)
                        .fontWeight(.medium)
                        .foregroundStyle(color.opacity(0.7))
                    ForEach(related) { lang in
                        HStack(spacing: 4) {
                            Text("•")
                                .font(font)
                                .foregroundStyle(color.opacity(0.5))
                            Text(lang.language + ":")
                                .font(font)
                                .foregroundStyle(color.opacity(0.7))
                            Text(lang.word)
                                .font(font)
                                .foregroundStyle(color)
                            if let trans = lang.transliteration, !trans.isEmpty {
                                Text("(\(trans))")
                                    .font(font)
                                    .foregroundStyle(color.opacity(0.7))
                            }
                        }
                    }
                }
            }
        }
    }
}
#endif
