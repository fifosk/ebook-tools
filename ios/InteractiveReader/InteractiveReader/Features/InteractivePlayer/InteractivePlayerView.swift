import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

struct InteractivePlayerView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss
    #if os(iOS)
    @Environment(\.verticalSizeClass) var verticalSizeClass
    #endif
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
    @State var readingBedCoordinator = AudioPlayerCoordinator(role: .ambient)
    @State var readingBedEnabled = true
    @State var scrubbedTime: Double?
    @State var visibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    @State var hasCustomTrackSelection = false
    @State var selectedSentenceID: Int?
    @State var linguistSelection: TextPlayerWordSelection?
    @State var linguistSelectionRange: TextPlayerWordSelectionRange?
    @State var linguistBubble: MyLinguistBubbleState?
    @State var linguistLookupTask: Task<Void, Never>?
    @State var linguistSpeechTask: Task<Void, Never>?
    @State var linguistAutoLookupTask: Task<Void, Never>?
    @AppStorage(MyLinguistPreferences.lookupLanguageKey) var storedLookupLanguage: String = ""
    @AppStorage(MyLinguistPreferences.llmModelKey) var storedLlmModel: String =
        MyLinguistPreferences.defaultLlmModel
    @AppStorage(MyLinguistPreferences.ttsVoiceKey) var storedTtsVoice: String = ""
    @State var availableLlmModels: [String] = []
    @State var didLoadLlmModels = false
    @State var voiceInventory: VoiceInventoryResponse?
    @State var didLoadVoiceInventory = false
    @State var isMenuVisible = false
    @State var resumePlaybackAfterMenu = false
    @State var bubbleFocusEnabled = false
    @AppStorage("player.headerCollapsed") var isHeaderCollapsed = false
    @State var frozenTranscriptSentences: [TextPlayerSentenceDisplay]?
    @State var frozenPlaybackPrimaryKind: TextPlayerVariantKind?
    @State var isShortcutHelpPinned = false
    @State var isShortcutHelpModifierActive = false
    @State var readingBedPauseTask: Task<Void, Never>?
    @AppStorage("interactive.trackFontScale") var trackFontScaleValue: Double =
        Double(InteractivePlayerView.defaultTrackFontScale)
    @AppStorage("interactive.autoScaleEnabled") var autoScaleEnabled: Bool = true
    @AppStorage("player.headerScale") var headerScaleValue: Double = 1.0
    @AppStorage("interactive.linguistFontScale") var linguistFontScaleValue: Double =
        Double(InteractivePlayerView.defaultLinguistFontScale)
    #if os(iOS)
    @State var headerMagnifyStartScale: CGFloat?
    @AppStorage("interactive.iPadSplitDirection") var iPadSplitDirectionRaw: String = "vertical"
    @AppStorage("interactive.iPadSplitRatio") var iPadSplitRatioValue: Double = 0.4
    @AppStorage("interactive.iPadBubblePinned") var iPadBubblePinned: Bool = false
    #endif
    @StateObject var bubbleKeyboardNavigator = iOSBubbleKeyboardNavigator()
    @StateObject var pronunciationSpeaker = PronunciationSpeaker()
    @State var bookmarks: [PlaybackBookmarkEntry] = []
    @StateObject var searchViewModel = MediaSearchViewModel()
    #if os(tvOS)
    @State var didSetInitialFocus = false
    @Namespace var searchFocusNamespace
    @Namespace var headerControlsNamespace
    @AppStorage("interactive.tvSplitEnabled") var tvSplitEnabled: Bool = false
    @AppStorage("interactive.tvBubblePinned") var tvBubblePinned: Bool = false
    #endif
    @FocusState var focusedArea: InteractivePlayerFocusArea?

    let playbackRates: [Double] = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5]
    let readingBedVolume: Double = 0.08
    let readingBedPauseDelayNanos: UInt64 = 250_000_000
    let linguistAutoLookupDelayNanos: UInt64 = 1_000_000_000
    let trackFontScaleStep: CGFloat = 0.1
    let trackFontScaleMin: CGFloat = 1.0
    let trackFontScaleMax: CGFloat = 3.0
    let headerScaleStep: CGFloat = 0.1
    let headerScaleMin: CGFloat = 0.7
    let headerScaleMax: CGFloat = 1.6
    let linguistFontScaleMin: CGFloat = 0.8
    var linguistFontScaleMax: CGFloat {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad ? 3.2 : 1.6
        #else
        return 1.6
        #endif
    }
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
            .onMoveCommand { direction in
                guard let chunk = viewModel.selectedChunk else { return }
                if focusedArea == .bubble {
                    // Handle vertical navigation out of bubble
                    // Let tvOS focus system handle left/right between bubble controls
                    switch direction {
                    case .up:
                        bubbleFocusEnabled = false
                        focusedArea = .transcript
                        return
                    case .down:
                        // Already at bottom, consume but do nothing
                        return
                    default:
                        // Left/right - don't return, let tvOS handle focus navigation
                        break
                    }
                }
                // Note: Menu is disabled on tvOS, but keep this check for safety
                if isMenuVisible, direction == .up {
                    hideMenu()
                    return
                }
                if focusedArea == .controls {
                    // Only handle up/down navigation in controls mode
                    // Let tvOS handle left/right to navigate between header buttons
                    switch direction {
                    case .down:
                        focusedArea = .transcript
                        return
                    case .up:
                        // Already at top, do nothing
                        return
                    default:
                        // Don't consume left/right - let tvOS focus system handle it
                        break
                    }
                }
                let isTranscriptFocus = focusedArea == .transcript || focusedArea == nil
                guard isTranscriptFocus else { return }
                switch direction {
                case .left:
                    if audioCoordinator.isPlaying {
                        viewModel.skipSentence(forward: false, preferredTrack: preferredSequenceTrack)
                    } else {
                        handleWordNavigation(-1, in: chunk)
                    }
                case .right:
                    if audioCoordinator.isPlaying {
                        viewModel.skipSentence(forward: true, preferredTrack: preferredSequenceTrack)
                    } else {
                        handleWordNavigation(1, in: chunk)
                    }
                case .up:
                    if audioCoordinator.isPlaying {
                        focusedArea = .controls
                    } else {
                        let moved = handleTrackNavigation(-1, in: chunk)
                        if moved {
                            bubbleFocusEnabled = false
                            focusedArea = .transcript
                        } else {
                            bubbleFocusEnabled = false
                            focusedArea = .controls
                        }
                    }
                case .down:
                    if audioCoordinator.isPlaying {
                        showMenu()
                    } else {
                        let moved = handleTrackNavigation(1, in: chunk)
                        if moved {
                            bubbleFocusEnabled = false
                            focusedArea = .transcript
                        } else if linguistBubble != nil {
                            bubbleFocusEnabled = true
                            focusedArea = .bubble
                        } else {
                            bubbleFocusEnabled = false
                            focusedArea = .transcript
                        }
                    }
                default:
                    break
                }
            }
            .onExitCommand {
                handleExitCommand()
            }
        #else
        baseContent
        #endif
    }

    #if os(tvOS)
    private func handleExitCommand() {
        // Handle bubble - when pinned, just defocus; when not pinned, close it
        if linguistBubble != nil {
            if tvBubblePinned && tvSplitEnabled {
                // Pinned bubble: just defocus back to transcript, don't close
                bubbleFocusEnabled = false
                focusedArea = .transcript
            } else {
                // Not pinned: close the bubble
                closeLinguistBubble()
                focusedArea = .transcript
                if !audioCoordinator.isPlaying {
                    audioCoordinator.play()
                }
            }
            return
        }
        // Return to transcript if in header controls
        if focusedArea == .controls {
            focusedArea = .transcript
            return
        }
        // Resume playback if paused
        if !audioCoordinator.isPlaying {
            // If we're on the last chunk and playback has ended, dismiss instead of restarting
            if isPlaybackFinished {
                dismiss()
                return
            }
            audioCoordinator.play()
            return
        }
        dismiss()
    }

    private var isPlaybackFinished: Bool {
        guard let chunk = viewModel.selectedChunk,
              let context = viewModel.jobContext else {
            return false
        }
        // Check if this is the last chunk
        let hasNextChunk = context.nextChunk(after: chunk.id) != nil
        if hasNextChunk {
            return false
        }
        // Check if playback position is near the end (within 1 second of duration)
        let duration = audioCoordinator.duration
        let currentTime = audioCoordinator.currentTime
        guard duration > 0 else { return false }
        return currentTime >= duration - 1.0
    }
    #endif
}
