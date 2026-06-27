import SwiftUI

extension AppleBookCreateView {
    func youtubeMetadataTextBinding(section: String?, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.youtubeMediaMetadataText(section: section, key: key)
            },
            set: { newValue in
                viewModel.updateYoutubeMediaMetadata(section: section, key: key, value: newValue)
            }
        )
    }

    func youtubeMetadataNumberBinding(section: String, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.youtubeMediaMetadataText(section: section, key: key)
            },
            set: { newValue in
                viewModel.updateYoutubeMediaMetadataNumber(section: section, key: key, value: newValue)
            }
        )
    }

    func youtubeMetadataNestedTextBinding(section: String, nestedKey: String, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.youtubeMediaMetadataNestedText(
                    section: section,
                    nestedKey: nestedKey,
                    keys: key == "medium" ? [key, "original"] : [key]
                )
            },
            set: { newValue in
                viewModel.updateYoutubeMediaMetadataNestedText(
                    section: section,
                    nestedKey: nestedKey,
                    key: key,
                    value: newValue
                )
            }
        )
    }

    func subtitleMetadataTextBinding(section: String?, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.subtitleMediaMetadataText(section: section, key: key)
            },
            set: { newValue in
                viewModel.updateSubtitleMediaMetadata(section: section, key: key, value: newValue)
            }
        )
    }

    func subtitleMetadataNumberBinding(section: String, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.subtitleMediaMetadataText(section: section, key: key)
            },
            set: { newValue in
                viewModel.updateSubtitleMediaMetadataNumber(section: section, key: key, value: newValue)
            }
        )
    }

    func subtitleMetadataNestedTextBinding(section: String, nestedKey: String, key: String) -> Binding<String> {
        Binding(
            get: {
                viewModel.subtitleMediaMetadataNestedText(
                    section: section,
                    nestedKey: nestedKey,
                    keys: key == "medium" ? [key, "original"] : [key]
                )
            },
            set: { newValue in
                viewModel.updateSubtitleMediaMetadataNestedText(
                    section: section,
                    nestedKey: nestedKey,
                    key: key,
                    value: newValue
                )
            }
        )
    }
}
