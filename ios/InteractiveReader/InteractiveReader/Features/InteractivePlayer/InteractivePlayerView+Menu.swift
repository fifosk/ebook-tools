import SwiftUI

extension InteractivePlayerView {
    var menuDragHandle: some View {
        #if os(tvOS)
        EmptyView()
        #else
        Capsule()
            .fill(Color.white.opacity(0.25))
            .frame(width: 36, height: 4)
            .frame(maxWidth: .infinity)
            .padding(.top, 2)
            .contentShape(Rectangle())
        #endif
    }

    func menuHeader(info: InteractivePlayerHeaderInfo, reelURLs: [URL]) -> some View {
        HStack(alignment: .top, spacing: 12) {
            if let coverURL = info.coverURL {
                AsyncImage(url: coverURL) { phase in
                    if let image = phase.image {
                        image.resizable().scaledToFill()
                    } else {
                        Color.gray.opacity(0.2)
                    }
                }
                .frame(width: menuCoverWidth, height: menuCoverHeight)
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
                )
            }
            VStack(alignment: .leading, spacing: 6) {
                Text(info.title.isEmpty ? "Untitled" : info.title)
                    .font(menuTitleFont)
                    .lineLimit(2)
                    .minimumScaleFactor(0.85)
                Text(info.author.isEmpty ? "Unknown author" : info.author)
                    .font(menuAuthorFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                    .foregroundStyle(.secondary)
                Text(info.itemTypeLabel)
                    .font(menuMetaFont)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.accentColor.opacity(0.2), in: Capsule())
            }
            if !reelURLs.isEmpty {
                Spacer(minLength: 12)
                InteractivePlayerImageReel(urls: reelURLs, height: menuCoverHeight)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
    }

    var menuCoverWidth: CGFloat {
        #if os(tvOS)
        return 96
        #else
        return 64
        #endif
    }

    var menuCoverHeight: CGFloat {
        #if os(tvOS)
        return 144
        #else
        return 96
        #endif
    }

    var menuTitleFont: Font {
        #if os(tvOS)
        return .title2
        #else
        return .title3
        #endif
    }

    var menuAuthorFont: Font {
        #if os(tvOS)
        return .callout
        #else
        return .callout
        #endif
    }

    var menuMetaFont: Font {
        #if os(tvOS)
        return .caption2
        #else
        return .caption
        #endif
    }

    @ViewBuilder
    var menuBackground: some View {
        #if os(tvOS)
        Color.black.opacity(0.78)
        #else
        Rectangle()
            .fill(.ultraThinMaterial)
        #endif
    }

    func imageReelURLs(for chunk: InteractiveChunk) -> [URL] {
        guard let showImageReel, showImageReel.wrappedValue else { return [] }
        guard hasImageReel(for: chunk) else { return [] }
        var urls: [URL] = []
        var seen: Set<String> = []
        for sentence in chunk.sentences {
            guard let path = resolveSentenceImagePath(sentence: sentence, chunk: chunk) else { continue }
            guard !seen.contains(path) else { continue }
            seen.insert(path)
            if let url = viewModel.resolvePath(path) {
                urls.append(url)
            }
            if urls.count >= 7 {
                break
            }
        }
        return urls
    }

    func resolveSentenceImagePath(sentence: InteractiveChunk.Sentence, chunk: InteractiveChunk) -> String? {
        if let rawPath = sentence.imagePath, let path = rawPath.nonEmptyValue {
            return path
        }
        guard let rangeFragment = chunk.rangeFragment?.nonEmptyValue else { return nil }
        let sentenceNumber = sentence.displayIndex ?? sentence.id
        guard sentenceNumber > 0 else { return nil }
        let padded = String(format: "%05d", sentenceNumber)
        return "media/images/\(rangeFragment)/sentence_\(padded).png"
    }

    @ViewBuilder
    func controlBar(_ chunk: InteractiveChunk) -> some View {
        let playbackTime = viewModel.playbackTime(for: chunk)
        let playbackDuration = viewModel.playbackDuration(for: chunk) ?? audioCoordinator.duration
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .center, spacing: 12) {
                chapterPicker()
                sentencePicker(for: chunk)
                textTrackPicker(for: chunk)
                audioPicker(for: chunk)
                readingBedPicker()
                speedPicker()
                settingsMenu()
                bookmarkMenu(for: chunk)
                #if os(tvOS)
                trackFontControls
                #endif
            }
            #if os(tvOS)
            .transaction { transaction in
                transaction.disablesAnimations = true
            }
            #endif
            if let range = chunk.rangeDescription {
                Text(range)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            if showsScrubber {
                PlaybackScrubberView(
                    coordinator: audioCoordinator,
                    currentTime: playbackTime,
                    duration: playbackDuration,
                    scrubbedTime: $scrubbedTime,
                    onSeek: { seekPlayback(to: $0, in: chunk) }
                )
            }
        }
    }

    #if os(tvOS)
    var trackFontControls: some View {
        let canDecrease = trackFontScale > trackFontScaleMin + 0.001
        let canIncrease = trackFontScale < trackFontScaleMax - 0.001
        return VStack(alignment: .leading, spacing: 4) {
            Text("Text Size")
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack(spacing: 6) {
                Button(action: decreaseTrackFontScale) {
                    Text("A-")
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 4)
                        .background(.black.opacity(0.3), in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(!canDecrease)
                .focused($focusedArea, equals: .controls)

                Button(action: increaseTrackFontScale) {
                    Text("A+")
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 4)
                        .background(.black.opacity(0.3), in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(!canIncrease)
                .focused($focusedArea, equals: .controls)
            }
        }
    }
    #endif

}
