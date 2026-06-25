import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

extension InteractivePlayerView {
    @ViewBuilder
    var speedPillView: some View {
        let currentRate = audioCoordinator.playbackRate
        let isNonDefault = abs(currentRate - 1.0) > 0.01
        let pill = Button {
            showSpeedOverlay.toggle()
        } label: {
            HStack(spacing: 4 * infoPillScale) {
                Image(systemName: "gauge.with.needle")
                    .font(speedPillIconFont)
                Text(playbackRateLabel(currentRate))
                    .font(speedPillLabelFont)
            }
            .foregroundStyle(Color.white.opacity(isNonDefault ? 1.0 : 0.85))
            .padding(.horizontal, (isTV ? 12 : 8) * infoPillScale)
            .padding(.vertical, (isTV ? 6 : 4) * infoPillScale)
            .background(
                Capsule()
                    .fill(Color.black.opacity(isNonDefault ? 0.7 : 0.55))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(isNonDefault ? 0.35 : 0.22), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Narration speed: \(playbackRateLabel(currentRate))")

        #if os(tvOS)
        pill
            .buttonStyle(TVMusicPillButtonStyle())
            .focused($focusedArea, equals: .controls)
            .sheet(isPresented: $showSpeedOverlay) {
                speedControlOverlay
            }
        #elseif os(iOS)
        if isPhone {
            pill
                .sheet(isPresented: $showSpeedOverlay) {
                    speedControlOverlay
                        .presentationDetents([.height(280)])
                        .presentationDragIndicator(.visible)
                }
        } else {
            pill
                .popover(isPresented: $showSpeedOverlay, arrowEdge: .top) {
                    speedControlOverlay
                }
        }
        #else
        pill
        #endif
    }

    @ViewBuilder
    var jumpPillView: some View {
        let currentSentence = selectedSentenceID ?? 1
        let pill = Button {
            showJumpOverlay.toggle()
        } label: {
            HStack(spacing: 4 * infoPillScale) {
                Image(systemName: "arrow.right.to.line")
                    .font(jumpPillIconFont)
                Text("#\(currentSentence)")
                    .font(jumpPillLabelFont)
            }
            .foregroundStyle(Color.white.opacity(0.85))
            .padding(.horizontal, (isTV ? 12 : 8) * infoPillScale)
            .padding(.vertical, (isTV ? 6 : 4) * infoPillScale)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.55))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.22), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Jump to sentence \(currentSentence)")

        #if os(tvOS)
        pill
            .buttonStyle(TVMusicPillButtonStyle())
            .focused($focusedArea, equals: .controls)
            .sheet(isPresented: $showJumpOverlay) {
                jumpControlOverlay
            }
        #elseif os(iOS)
        if isPhone {
            pill
                .sheet(isPresented: $showJumpOverlay) {
                    jumpControlOverlay
                        .presentationDetents([.medium])
                        .presentationDragIndicator(.visible)
                }
        } else {
            pill
                .popover(isPresented: $showJumpOverlay, arrowEdge: .top) {
                    jumpControlOverlay
                }
        }
        #else
        pill
        #endif
    }

    @ViewBuilder
    var sleepTimerPillView: some View {
        let menu = SleepTimerMenu(
            timer: sleepTimer,
            isTV: isTV,
            sizeScale: infoPillScale,
            onStart: startSleepTimer,
            onCancel: cancelSleepTimer
        )
        #if os(tvOS)
        menu
            .buttonStyle(TVMusicPillButtonStyle())
            .focused($focusedArea, equals: .controls)
        #else
        menu
        #endif
    }

    private var speedPillIconFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .callout : .caption1
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * infoPillScale, weight: .semibold)
        #else
        return .system(size: 12 * infoPillScale, weight: .semibold)
        #endif
    }

    private var speedPillLabelFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .caption1 : .caption2
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * infoPillScale, weight: .medium)
        #else
        return .system(size: 10 * infoPillScale, weight: .medium)
        #endif
    }

    private var jumpPillIconFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .callout : .caption1
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * infoPillScale, weight: .semibold)
        #else
        return .system(size: 12 * infoPillScale, weight: .semibold)
        #endif
    }

    private var jumpPillLabelFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .caption1 : .caption2
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * infoPillScale, weight: .medium)
        #else
        return .system(size: 10 * infoPillScale, weight: .medium)
        #endif
    }

    private var speedControlOverlay: some View {
        SpeedControlOverlayView(
            currentRate: audioCoordinator.playbackRate,
            rates: playbackRates,
            onSelectRate: { rate in
                audioCoordinator.setPlaybackRate(rate)
            },
            rateLabel: playbackRateLabel
        )
    }

    private var jumpControlOverlay: some View {
        JumpControlOverlayView(
            chapters: scopedChapterEntries,
            currentSentence: selectedSentenceID ?? 1,
            sentenceBounds: jobSentenceBounds,
            chapterLabel: chapterLabel,
            onJumpToSentence: { sentence in
                viewModel.jumpToSentence(sentence, autoPlay: audioCoordinator.isPlaybackRequested)
                showJumpOverlay = false
            },
            onJumpToChapter: { chapter in
                selectedSentenceID = chapter.startSentence
                viewModel.jumpToSentence(chapter.startSentence, autoPlay: audioCoordinator.isPlaybackRequested)
                showJumpOverlay = false
            }
        )
    }

    func startSleepTimer(_ option: SleepTimerOption) {
        sleepTimer.start(option: option, onExpire: handleSleepTimerExpired)
    }

    func cancelSleepTimer() {
        sleepTimer.cancel()
    }

    func handleSleepTimerExpired() {
        audioCoordinator.pause()
        readingBedCoordinator.pause()
        if useAppleMusicForBed {
            musicCoordinator.pause()
        }
    }
}

struct SpeedControlOverlayView: View {
    let currentRate: Double
    let rates: [Double]
    let onSelectRate: (Double) -> Void
    let rateLabel: (Double) -> String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Narration Speed")
                .font(.subheadline.weight(.medium))

            #if os(iOS)
            VStack(spacing: 8) {
                HStack {
                    Text("Slower")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(rateLabel(currentRate))
                        .font(.body.weight(.semibold).monospacedDigit())
                    Spacer()
                    Text("Faster")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                Slider(
                    value: Binding(
                        get: { currentRate },
                        set: { newValue in
                            if let closest = rates.min(by: { abs($0 - newValue) < abs($1 - newValue) }) {
                                onSelectRate(closest)
                            }
                        }
                    ),
                    in: (rates.first ?? 0.5)...(rates.last ?? 1.5),
                    step: 0.1
                )
                .tint(.accentColor)

                HStack(spacing: 8) {
                    ForEach([0.5, 0.8, 1.0, 1.2, 1.5], id: \.self) { rate in
                        Button {
                            onSelectRate(rate)
                        } label: {
                            Text(rateLabel(rate))
                                .font(.caption2.weight(isCurrentRate(rate) ? .bold : .regular))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(
                                    Capsule()
                                        .fill(isCurrentRate(rate) ? Color.accentColor : Color.secondary.opacity(0.2))
                                )
                                .foregroundStyle(isCurrentRate(rate) ? .white : .primary)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            #else
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 12) {
                ForEach(rates, id: \.self) { rate in
                    Button {
                        onSelectRate(rate)
                    } label: {
                        Text(rateLabel(rate))
                            .font(.body.weight(isCurrentRate(rate) ? .bold : .regular))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(isCurrentRate(rate) ? Color.accentColor : Color.secondary.opacity(0.2))
                            )
                            .foregroundStyle(isCurrentRate(rate) ? .white : .primary)
                    }
                    .buttonStyle(.plain)
                }
            }
            #endif
        }
        .padding(16)
        #if os(iOS)
        .frame(width: isPad ? 300 : nil)
        .background {
            RoundedRectangle(cornerRadius: 16)
                .fill(.regularMaterial)
        }
        .foregroundStyle(.primary)
        #endif
    }

    private func isCurrentRate(_ rate: Double) -> Bool {
        abs(rate - currentRate) < 0.01
    }

    private var isPad: Bool { PlatformAdapter.isPad }
}
