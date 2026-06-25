import SwiftUI
#if os(iOS)
import UIKit
#endif

// MARK: - Type Aliases for Backwards Compatibility

/// Backwards compatibility alias for MyLinguistBubbleStatus.
typealias MyLinguistBubbleStatus = LinguistBubbleStatus

/// Backwards compatibility alias for VideoLinguistBubbleStatus.
typealias VideoLinguistBubbleStatus = LinguistBubbleStatus

/// Backwards compatibility state for Interactive Player.
struct MyLinguistBubbleState: Equatable {
    let query: String
    let status: LinguistBubbleStatus
    let answer: String?
    let model: String?
    var lookupSource: LinguistLookupSource? = nil
    /// Audio reference from lookup cache - allows playing word from narration audio.
    var cachedAudioRef: LookupCacheAudioRef? = nil

    var asLinguistBubbleState: LinguistBubbleState {
        LinguistBubbleState(
            query: query,
            status: status,
            answer: answer,
            model: model,
            lookupSource: lookupSource,
            cachedAudioRef: cachedAudioRef
        )
    }
}

/// Backwards compatibility state for Video Player.
struct VideoLinguistBubbleState: Equatable {
    let query: String
    let status: LinguistBubbleStatus
    let answer: String?
    let model: String?
    var lookupSource: LinguistLookupSource? = nil
    /// Audio reference from lookup cache - allows playing word from narration audio.
    var cachedAudioRef: LookupCacheAudioRef? = nil

    var asLinguistBubbleState: LinguistBubbleState {
        LinguistBubbleState(
            query: query,
            status: status,
            answer: answer,
            model: model,
            lookupSource: lookupSource,
            cachedAudioRef: cachedAudioRef
        )
    }
}

// MARK: - Backwards Compatible View Wrappers

/// Wrapper for Video Player that maintains the original API.
struct VideoLinguistBubbleView: View {
    let bubble: VideoLinguistBubbleState
    let fontScale: CGFloat
    let canIncreaseFont: Bool
    let canDecreaseFont: Bool
    let lookupLanguage: String
    let lookupLanguageOptions: [String]
    let onLookupLanguageChange: (String) -> Void
    let llmModel: String
    let llmModelOptions: [String]
    let onLlmModelChange: (String) -> Void
    var ttsVoice: String?
    var ttsVoiceOptions: [String]
    var onTtsVoiceChange: ((String?) -> Void)?
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onResetFont: (() -> Void)?
    let onClose: () -> Void
    let onMagnify: ((CGFloat) -> Void)?
    let onPlayFromNarration: (() -> Void)?
    let onReadAloud: (() -> Void)?

    #if os(tvOS)
    let isFocusEnabled: Bool
    let onBubbleFocus: (() -> Void)?

    init(
        bubble: VideoLinguistBubbleState,
        fontScale: CGFloat,
        canIncreaseFont: Bool,
        canDecreaseFont: Bool,
        lookupLanguage: String,
        isFocusEnabled: Bool,
        onBubbleFocus: (() -> Void)?,
        lookupLanguageOptions: [String],
        onLookupLanguageChange: @escaping (String) -> Void,
        llmModel: String,
        llmModelOptions: [String],
        onLlmModelChange: @escaping (String) -> Void,
        ttsVoice: String? = nil,
        ttsVoiceOptions: [String] = [],
        onTtsVoiceChange: ((String?) -> Void)? = nil,
        onIncreaseFont: @escaping () -> Void,
        onDecreaseFont: @escaping () -> Void,
        onResetFont: (() -> Void)?,
        onClose: @escaping () -> Void,
        onMagnify: ((CGFloat) -> Void)?,
        onPlayFromNarration: (() -> Void)? = nil,
        onReadAloud: (() -> Void)? = nil
    ) {
        self.bubble = bubble
        self.fontScale = fontScale
        self.canIncreaseFont = canIncreaseFont
        self.canDecreaseFont = canDecreaseFont
        self.lookupLanguage = lookupLanguage
        self.isFocusEnabled = isFocusEnabled
        self.onBubbleFocus = onBubbleFocus
        self.lookupLanguageOptions = lookupLanguageOptions
        self.onLookupLanguageChange = onLookupLanguageChange
        self.llmModel = llmModel
        self.llmModelOptions = llmModelOptions
        self.onLlmModelChange = onLlmModelChange
        self.ttsVoice = ttsVoice
        self.ttsVoiceOptions = ttsVoiceOptions
        self.onTtsVoiceChange = onTtsVoiceChange
        self.onIncreaseFont = onIncreaseFont
        self.onDecreaseFont = onDecreaseFont
        self.onResetFont = onResetFont
        self.onClose = onClose
        self.onMagnify = onMagnify
        self.onPlayFromNarration = onPlayFromNarration
        self.onReadAloud = onReadAloud
    }
    #else
    init(
        bubble: VideoLinguistBubbleState,
        fontScale: CGFloat,
        canIncreaseFont: Bool,
        canDecreaseFont: Bool,
        lookupLanguage: String,
        lookupLanguageOptions: [String],
        onLookupLanguageChange: @escaping (String) -> Void,
        llmModel: String,
        llmModelOptions: [String],
        onLlmModelChange: @escaping (String) -> Void,
        ttsVoice: String? = nil,
        ttsVoiceOptions: [String] = [],
        onTtsVoiceChange: ((String?) -> Void)? = nil,
        onIncreaseFont: @escaping () -> Void,
        onDecreaseFont: @escaping () -> Void,
        onResetFont: (() -> Void)?,
        onClose: @escaping () -> Void,
        onMagnify: ((CGFloat) -> Void)?,
        onPlayFromNarration: (() -> Void)? = nil,
        onReadAloud: (() -> Void)? = nil
    ) {
        self.bubble = bubble
        self.fontScale = fontScale
        self.canIncreaseFont = canIncreaseFont
        self.canDecreaseFont = canDecreaseFont
        self.lookupLanguage = lookupLanguage
        self.lookupLanguageOptions = lookupLanguageOptions
        self.onLookupLanguageChange = onLookupLanguageChange
        self.llmModel = llmModel
        self.llmModelOptions = llmModelOptions
        self.onLlmModelChange = onLlmModelChange
        self.ttsVoice = ttsVoice
        self.ttsVoiceOptions = ttsVoiceOptions
        self.onTtsVoiceChange = onTtsVoiceChange
        self.onIncreaseFont = onIncreaseFont
        self.onDecreaseFont = onDecreaseFont
        self.onResetFont = onResetFont
        self.onClose = onClose
        self.onMagnify = onMagnify
        self.onPlayFromNarration = onPlayFromNarration
        self.onReadAloud = onReadAloud
    }
    #endif

    private var bubbleConfiguration: LinguistBubbleConfiguration {
        var config = LinguistBubbleConfiguration(
            fontScale: fontScale,
            canIncreaseFont: canIncreaseFont,
            canDecreaseFont: canDecreaseFont,
            lookupLanguage: lookupLanguage,
            lookupLanguageOptions: lookupLanguageOptions,
            llmModel: llmModel,
            llmModelOptions: llmModelOptions
        )
        config.ttsVoice = ttsVoice
        config.ttsVoiceOptions = ttsVoiceOptions
        #if os(iOS)
        if UIDevice.current.userInterfaceIdiom == .pad {
            config.uiScale = 1.5
        }
        #endif
        return config
    }

    private var bubbleActions: LinguistBubbleActions {
        var actions = LinguistBubbleActions(
            onLookupLanguageChange: onLookupLanguageChange,
            onLlmModelChange: onLlmModelChange,
            onIncreaseFont: onIncreaseFont,
            onDecreaseFont: onDecreaseFont,
            onClose: onClose,
            onTtsVoiceChange: onTtsVoiceChange,
            onResetFont: onResetFont,
            onMagnify: onMagnify,
            onBubbleFocus: {
                #if os(tvOS)
                onBubbleFocus?()
                #endif
            }
        )
        actions.onPlayFromNarration = onPlayFromNarration
        actions.onReadAloud = onReadAloud
        return actions
    }

    var body: some View {
        #if os(tvOS)
        LinguistBubbleView(
            state: bubble.asLinguistBubbleState,
            configuration: bubbleConfiguration,
            actions: bubbleActions,
            isFocusEnabled: isFocusEnabled
        )
        #else
        LinguistBubbleView(
            state: bubble.asLinguistBubbleState,
            configuration: bubbleConfiguration,
            actions: bubbleActions
        )
        #endif
    }
}
