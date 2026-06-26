import AVFoundation

final class PronunciationSpeaker: NSObject, ObservableObject, @preconcurrency AVAudioPlayerDelegate {
    private static let minimumAudibleDuration: TimeInterval = 0.05

    private let synthesizer = AVSpeechSynthesizer()
    private var audioPlayer: AVAudioPlayer?
    @MainActor var onPlaybackStarted: (() -> Void)?

    @MainActor
    @discardableResult
    func playAudio(_ data: Data) -> Bool {
        stop()
        configureAudioSession()
        do {
            let player = try AVAudioPlayer(data: data)
            guard player.duration.isFinite, player.duration >= Self.minimumAudibleDuration else {
                audioPlayer = nil
                return false
            }
            player.delegate = self
            player.volume = 1.0
            player.prepareToPlay()
            let didStart = player.play()
            guard didStart else {
                audioPlayer = nil
                return false
            }
            audioPlayer = player
            onPlaybackStarted?()
            return true
        } catch {
            audioPlayer = nil
            return false
        }
    }

    @MainActor
    func speakFallback(_ text: String, language: String?) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        stop()
        configureAudioSession()
        let utterance = AVSpeechUtterance(string: trimmed)
        if let language, let voice = AVSpeechSynthesisVoice(language: language) {
            utterance.voice = voice
        }
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        synthesizer.speak(utterance)
        onPlaybackStarted?()
    }

    @MainActor
    func stop() {
        synthesizer.stopSpeaking(at: .immediate)
        audioPlayer?.stop()
        audioPlayer = nil
    }

    @MainActor
    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        audioPlayer = nil
    }

    @MainActor
    private func configureAudioSession() {
        #if os(iOS) || os(tvOS)
        let session = AVAudioSession.sharedInstance()
        do {
            // Prefer ducking active playback, but retry with simpler categories because
            // tvOS can reject richer option sets after video playback owns the session.
            let options: AVAudioSession.CategoryOptions = [.allowAirPlay, .mixWithOthers, .duckOthers]
            try session.setCategory(.playback, mode: .spokenAudio, options: options)
        } catch {
            do {
                try session.setCategory(.playback, mode: .spokenAudio, options: [.allowAirPlay])
            } catch {
                try? session.setCategory(.playback, mode: .default, options: [])
            }
        }
        try? session.setActive(true)
        #endif
    }
}
