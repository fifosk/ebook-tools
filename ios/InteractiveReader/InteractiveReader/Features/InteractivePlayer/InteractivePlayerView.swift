import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

struct InteractivePlayerView: View {
    @EnvironmentObject var appState: AppState
    @ObservedObject var viewModel: InteractivePlayerViewModel
    @ObservedObject var audioCoordinator: AudioPlayerCoordinator
    let showImageReel: Binding<Bool>?
    let showsScrubber: Bool
    let linguistInputLanguage: String
    let linguistLookupLanguage: String
    let linguistExplanationLanguage: String
    let headerInfo: InteractivePlayerHeaderInfo?
    let bookmarkUserId: String?
    let bookmarkJobId: String?
    let bookmarkItemType: String?
    @State var readingBedCoordinator = AudioPlayerCoordinator()
    @State var readingBedEnabled = true
    @State var scrubbedTime: Double?
    @State var visibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    @State var hasCustomTrackSelection = false
    @State var selectedSentenceID: Int?
    @State var linguistSelection: TextPlayerWordSelection?
    @State var linguistBubble: MyLinguistBubbleState?
    @State var linguistLookupTask: Task<Void, Never>?
    @State var linguistSpeechTask: Task<Void, Never>?
    @State var linguistAutoLookupTask: Task<Void, Never>?
    @AppStorage(MyLinguistPreferences.lookupLanguageKey) var storedLookupLanguage: String = ""
    @AppStorage(MyLinguistPreferences.llmModelKey) var storedLlmModel: String =
        MyLinguistPreferences.defaultLlmModel
    @State var availableLlmModels: [String] = []
    @State var didLoadLlmModels = false
    @State var isMenuVisible = false
    @AppStorage("player.headerCollapsed") var isHeaderCollapsed = false
    @State var frozenTranscriptSentences: [TextPlayerSentenceDisplay]?
    @State var isShortcutHelpPinned = false
    @State var isShortcutHelpModifierActive = false
    @State var readingBedPauseTask: Task<Void, Never>?
    @AppStorage("interactive.trackFontScale") var trackFontScaleValue: Double =
        Double(InteractivePlayerView.defaultTrackFontScale)
    @AppStorage("interactive.linguistFontScale") var linguistFontScaleValue: Double =
        Double(InteractivePlayerView.defaultLinguistFontScale)
    @StateObject var pronunciationSpeaker = PronunciationSpeaker()
    @State var bookmarks: [PlaybackBookmarkEntry] = []
    #if os(tvOS)
    @State var didSetInitialFocus = false
    #endif
    @FocusState var focusedArea: InteractivePlayerFocusArea?

    let playbackRates: [Double] = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5]
    let readingBedVolume: Double = 0.08
    let readingBedPauseDelayNanos: UInt64 = 250_000_000
    let linguistAutoLookupDelayNanos: UInt64 = 1_000_000_000
    let trackFontScaleStep: CGFloat = 0.1
    let trackFontScaleMin: CGFloat = 1.0
    let trackFontScaleMax: CGFloat = 3.0
    let linguistFontScaleMin: CGFloat = 0.8
    let linguistFontScaleMax: CGFloat = 1.6
    let linguistFontScaleStep: CGFloat = 0.05
    private static var defaultTrackFontScale: CGFloat {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad ? 2.0 : 1.0
        #else
        return 1.0
        #endif
    }
    private static let defaultLinguistFontScale: CGFloat = 1.2
    var resolvedBookmarkUserId: String {
        bookmarkUserId?.nonEmptyValue ?? "anonymous"
    }
    var resolvedBookmarkJobId: String? {
        bookmarkJobId?.nonEmptyValue ?? viewModel.jobId
    }
    var resolvedBookmarkItemType: String {
        bookmarkItemType?.nonEmptyValue ?? headerInfo?.itemTypeLabel.lowercased() ?? "book"
    }
    var bookmarkIdentityKey: String {
        "\(resolvedBookmarkUserId)|\(resolvedBookmarkJobId ?? "")"
    }
    var canUseBookmarks: Bool {
        resolvedBookmarkJobId != nil
    }

    init(
        viewModel: InteractivePlayerViewModel,
        audioCoordinator: AudioPlayerCoordinator,
        showImageReel: Binding<Bool>? = nil,
        showsScrubber: Bool = true,
        linguistInputLanguage: String = "",
        linguistLookupLanguage: String = "English",
        linguistExplanationLanguage: String = "English",
        headerInfo: InteractivePlayerHeaderInfo? = nil,
        bookmarkUserId: String? = nil,
        bookmarkJobId: String? = nil,
        bookmarkItemType: String? = nil
    ) {
        self._viewModel = ObservedObject(wrappedValue: viewModel)
        self._audioCoordinator = ObservedObject(wrappedValue: audioCoordinator)
        self.showImageReel = showImageReel
        self.showsScrubber = showsScrubber
        self.linguistInputLanguage = linguistInputLanguage
        self.linguistLookupLanguage = linguistLookupLanguage
        self.linguistExplanationLanguage = linguistExplanationLanguage
        self.headerInfo = headerInfo
        self.bookmarkUserId = bookmarkUserId
        self.bookmarkJobId = bookmarkJobId
        self.bookmarkItemType = bookmarkItemType
    }

    var body: some View {
        #if os(tvOS)
        baseContent
            .onPlayPauseCommand {
                audioCoordinator.togglePlayback()
            }
            .applyIf(!isMenuVisible) { view in
                view.onMoveCommand { direction in
                    guard let chunk = viewModel.selectedChunk else { return }
                    if focusedArea == .controls {
                        if direction == .down {
                            focusedArea = .transcript
                        }
                        return
                    }
                    guard focusedArea == .transcript else { return }
                    switch direction {
                    case .left:
                        if audioCoordinator.isPlaying {
                            viewModel.skipSentence(forward: false)
                        } else {
                            handleWordNavigation(-1, in: chunk)
                        }
                    case .right:
                        if audioCoordinator.isPlaying {
                            viewModel.skipSentence(forward: true)
                        } else {
                            handleWordNavigation(1, in: chunk)
                        }
                    case .up:
                        if audioCoordinator.isPlaying {
                            focusedArea = .controls
                        } else {
                            handleTrackNavigation(-1, in: chunk)
                        }
                    case .down:
                        if audioCoordinator.isPlaying {
                            showMenu()
                        } else {
                            handleTrackNavigation(1, in: chunk)
                        }
                    default:
                        break
                    }
                }
            }
            .applyIf(isMenuVisible) { view in
                view.onMoveCommand { direction in
                    if direction == .up {
                        hideMenu()
                    }
                }
            }
        #else
        baseContent
        #endif
    }

}
