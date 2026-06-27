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
    @AppStorage(MusicPreferences.readingBedEnabledKey) var readingBedEnabled = true
    @State var showMusicPicker = false
    @State var showMusicOverlay = false
    @State var showSpeedOverlay = false
    @State var showJumpOverlay = false
    @StateObject var sleepTimer = SleepTimerController()
    @StateObject var musicCoordinator = MusicKitCoordinator.shared
    @AppStorage(MusicPreferences.useAppleMusicKey) var useAppleMusicForBed = false
    @AppStorage(MusicPreferences.musicVolumeKey) var musicVolume: Double = MusicPreferences.defaultMusicVolume
    @AppStorage(MusicPreferences.appleMusicMixInitializedKey) var didInitializeAppleMusicMix = false
    @State var scrubbedTime: Double?
    @State var headerSentenceSliderValue: Double?
    @State var isHeaderSentenceSliderEditing = false
    @State var phoneProgressFooterAutoHideTask: Task<Void, Never>?
    @AppStorage("interactive.phoneProgressFooterVisible") var phoneProgressFooterVisible = false
    @State var headerOverlayMeasuredHeight: CGFloat = 0
    @State var visibleTracks: Set<TextPlayerVariantKind> = [.original, .translation, .transliteration]
    @State var hasCustomTrackSelection = false
    /// Central manager for audio mode and track toggles
    /// This is the single source of truth for whether original/translation audio is enabled
    @StateObject var audioModeManager = AudioModeManager()
    @State var selectedSentenceID: Int?
    @State var linguistSelection: TextPlayerWordSelection?
    @State var linguistSelectionRange: TextPlayerWordSelectionRange?
    @State var linguistVM = MyLinguistBubbleViewModel()
    @AppStorage(MyLinguistPreferences.lookupLanguageKey) var storedLookupLanguage: String = ""
    @AppStorage(MyLinguistPreferences.llmModelKey) var storedLlmModel: String =
        MyLinguistPreferences.defaultLlmModel
    @AppStorage(MyLinguistPreferences.ttsVoiceKey) var storedTtsVoice: String = ""
    @State var isMenuVisible = false
    @State var showBookMetadataOverlay = false
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
    @State var bookmarks: [PlaybackBookmarkEntry] = []
    @StateObject var musicSearchService = MusicSearchService()
    @StateObject var searchViewModel = MediaSearchViewModel()
    #if os(tvOS)
    @State var didSetInitialFocus = false
    @Namespace var searchFocusNamespace
    @Namespace var headerControlsNamespace
    @AppStorage("interactive.tvSplitEnabled") var tvSplitEnabled: Bool = false
    @AppStorage("interactive.tvBubblePinned") var tvBubblePinned: Bool = false
    #endif
    @FocusState var focusedArea: InteractivePlayerFocusArea?

    let playbackRates: [Double] = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
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

    // MARK: - ViewModel Bridge Properties

    /// Bridge to ViewModel's bubble state — allows existing code to read/write `linguistBubble` unchanged.
    var linguistBubble: MyLinguistBubbleState? {
        get { linguistVM.bubble }
        nonmutating set { linguistVM.bubble = newValue }
    }

    var linguistLookupTask: Task<Void, Never>? {
        get { linguistVM.lookupTask }
    }

    var linguistSpeechTask: Task<Void, Never>? {
        get { linguistVM.speechTask }
    }

    var linguistAutoLookupTask: Task<Void, Never>? {
        get { linguistVM.autoLookupTask }
        nonmutating set { linguistVM.autoLookupTask = newValue }
    }

    var availableLlmModels: [String] {
        get { linguistVM.availableLlmModels }
        nonmutating set { linguistVM.availableLlmModels = newValue }
    }

    var didLoadLlmModels: Bool {
        get { linguistVM.didLoadLlmModels }
        nonmutating set { linguistVM.didLoadLlmModels = newValue }
    }

    var voiceInventory: VoiceInventoryResponse? {
        get { linguistVM.voiceInventory }
        nonmutating set { linguistVM.voiceInventory = newValue }
    }

    var didLoadVoiceInventory: Bool {
        get { linguistVM.didLoadVoiceInventory }
        nonmutating set { linguistVM.didLoadVoiceInventory = newValue }
    }

    var pronunciationSpeaker: PronunciationSpeaker {
        linguistVM.pronunciationSpeaker
    }

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
            .accessibilityIdentifier("interactivePlayerView")
            .overlay(alignment: .topLeading) {
                Text("Interactive Player")
                    .frame(width: 1, height: 1)
                    .opacity(0.001)
                    .accessibilityIdentifier("interactivePlayerView")
            }
            .onPlayPauseCommand {
                handlePlaybackToggleCommand()
            }
            .onMoveCommand(perform: handleTVMoveCommand)
            .onExitCommand {
                handleExitCommand()
            }
        #else
        baseContent
            .accessibilityIdentifier("interactivePlayerView")
        #endif
    }

    #if os(tvOS)
    private func handleTVMoveCommand(_ direction: MoveCommandDirection) {
        guard let chunk = viewModel.selectedChunk else { return }
        if handleBubbleMoveCommand(direction) {
            return
        }
        if handleMenuMoveCommand(direction) {
            return
        }
        if handleControlsMoveCommand(direction) {
            return
        }
        if handleProgressMoveCommand(direction, chunk: chunk) {
            return
        }
        handleTranscriptMoveCommand(direction, chunk: chunk)
    }

    private func handleBubbleMoveCommand(_ direction: MoveCommandDirection) -> Bool {
        guard focusedArea == .bubble else { return false }
        // Let tvOS focus system handle left/right between bubble controls.
        switch direction {
        case .up:
            bubbleFocusEnabled = false
            focusedArea = .transcript
            return true
        case .down:
            return true
        default:
            return false
        }
    }

    private func handleMenuMoveCommand(_ direction: MoveCommandDirection) -> Bool {
        // Menu is disabled on tvOS, but keep this check for safety.
        guard isMenuVisible, direction == .up else { return false }
        hideMenu()
        return true
    }

    private func handleControlsMoveCommand(_ direction: MoveCommandDirection) -> Bool {
        guard focusedArea == .controls else { return false }
        // Let tvOS focus system handle left/right between header buttons.
        switch direction {
        case .down:
            focusedArea = .transcript
            return true
        case .up:
            return true
        default:
            return false
        }
    }

    private func handleProgressMoveCommand(_ direction: MoveCommandDirection, chunk: InteractiveChunk) -> Bool {
        guard focusedArea == .progress else { return false }
        switch direction {
        case .up, .down:
            focusedArea = .transcript
            return true
        case .left:
            handleTVProgressFooterHorizontalMove(-1, chunk: chunk)
            return true
        case .right:
            handleTVProgressFooterHorizontalMove(1, chunk: chunk)
            return true
        default:
            return false
        }
    }

    func handleTVProgressFooterMoveCommand(_ direction: MoveCommandDirection) {
        guard focusedArea == .progress else { return }
        switch direction {
        case .up, .down:
            focusedArea = .transcript
        case .left, .right:
            guard let chunk = viewModel.selectedChunk else { return }
            handleTVProgressFooterHorizontalMove(direction == .left ? -1 : 1, chunk: chunk)
        default:
            break
        }
    }

    private func handleTVProgressFooterHorizontalMove(_ delta: Int, chunk: InteractiveChunk) {
        guard let range = headerSentenceProgressRange(for: chunk) else { return }
        let current = headerSentenceProgressValue(for: chunk).rounded()
        let nextValue = min(max(current + Double(delta), range.lowerBound), range.upperBound)
        guard nextValue != current else { return }
        handleHeaderSentenceProgressChange(nextValue)
        handleHeaderSentenceProgressEditingChanged(false)
    }

    private func handleTranscriptMoveCommand(_ direction: MoveCommandDirection, chunk: InteractiveChunk) {
        let isTranscriptFocus = focusedArea == .transcript || focusedArea == nil
        guard isTranscriptFocus else { return }
        switch direction {
        case .left:
            handleTranscriptHorizontalMove(-1, chunk: chunk)
        case .right:
            handleTranscriptHorizontalMove(1, chunk: chunk)
        case .up:
            handleTranscriptUpMove(chunk)
        case .down:
            handleTranscriptDownMove(chunk)
        default:
            break
        }
    }

    private func handleTranscriptHorizontalMove(_ delta: Int, chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            handleSentenceSkip(delta, in: chunk)
        } else {
            handleWordNavigation(delta, in: chunk)
        }
    }

    private func handleTranscriptUpMove(_ chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            focusedArea = .controls
        } else {
            let moved = handleTrackNavigation(-1, in: chunk)
            bubbleFocusEnabled = false
            focusedArea = moved ? .transcript : .controls
        }
    }

    private func handleTranscriptDownMove(_ chunk: InteractiveChunk) {
        if headerSentenceProgressRange(for: chunk) != nil {
            focusedArea = .progress
        } else if audioCoordinator.isPlaying {
            focusedArea = .progress
        } else {
            let moved = handleTrackNavigation(1, in: chunk)
            if moved {
                bubbleFocusEnabled = false
                focusedArea = .transcript
            } else if linguistBubble != nil {
                bubbleFocusEnabled = true
                focusedArea = .bubble
            } else if headerSentenceProgressRange(for: chunk) != nil {
                bubbleFocusEnabled = false
                focusedArea = .progress
            } else {
                bubbleFocusEnabled = false
                focusedArea = .transcript
            }
        }
    }

    private func handleExitCommand() {
        // Handle bubble - when pinned, just defocus; when not pinned, close it
        if linguistBubble != nil {
            if tvBubblePinned && tvSplitEnabled {
                // Pinned bubble with focus: just defocus back to transcript, don't close
                if bubbleFocusEnabled || focusedArea == .bubble {
                    bubbleFocusEnabled = false
                    focusedArea = .transcript
                    return
                }
                // Pinned bubble but focus already on transcript: dismiss to navigate back
                dismiss()
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

    func handleTVProgressFooterFocusChanged(_ isFocused: Bool) {
        #if os(tvOS)
        if isFocused {
            focusedArea = .progress
        } else if focusedArea == .progress {
            focusedArea = .transcript
        }
        #endif
    }
}
