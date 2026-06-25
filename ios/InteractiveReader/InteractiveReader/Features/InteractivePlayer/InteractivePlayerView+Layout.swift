import SwiftUI

extension InteractivePlayerView {
    var baseContent: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            playerContent
        }
    }

    var playerStack: some View {
        ZStack(alignment: .top) {
            playerMainLayer
                #if os(tvOS)
                .disabled(searchViewModel.isExpanded)
                #endif
            playerOverlayLayer
        }
    }

    @ViewBuilder
    private var playerMainLayer: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let chunk = viewModel.selectedChunk {
                interactiveContent(for: chunk)
            } else {
                Text("No interactive chunks were returned for this job.")
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    @ViewBuilder
    private var playerOverlayLayer: some View {
        // Background overlays - disabled when search is active on tvOS
        Group {
            if let chunk = viewModel.selectedChunk, (shouldShowHeaderOverlay || isTV) {
                playerInfoOverlay(for: chunk)
            }
            if let chunk = viewModel.selectedChunk {
                menuOverlay(for: chunk)
            }
            headerToggleButton
        }
        #if os(tvOS)
        .disabled(searchViewModel.isExpanded)
        #endif

        // Search overlay - on top and captures focus
        searchOverlayContainer

        // Other layers
        bookMetadataOverlayContainer
        trackpadSwipeLayer
        shortcutHelpOverlay
        keyboardShortcutLayer
    }

    @ViewBuilder
    private var bookMetadataOverlayContainer: some View {
        #if os(iOS)
        if showBookMetadataOverlay, let headerInfo {
            ZStack {
                Color.black.opacity(0.48)
                    .ignoresSafeArea()
                    .onTapGesture(perform: dismissBookMetadataOverlay)
                VStack {
                    Spacer()
                    InteractivePlayerBookMetadataOverlay(
                        info: headerInfo,
                        isPad: isPad,
                        onDismiss: dismissBookMetadataOverlay
                    )
                    .padding(.horizontal, isPad ? 40 : 16)
                    .padding(.bottom, isPad ? 44 : 24)
                }
            }
            .transition(.opacity)
            .zIndex(4)
            .accessibilityIdentifier("interactiveReaderBookMetadataOverlay")
        }
        #endif
    }

    @ViewBuilder
    private var searchOverlayContainer: some View {
        if searchViewModel.isExpanded {
            ZStack {
                // Background dismissal area
                Color.black.opacity(0.3)
                    #if !os(tvOS)
                    .onTapGesture(perform: dismissTextSearchOverlay)
                    #endif

                // Search content
                VStack {
                    HStack {
                        Spacer()
                        searchOverlayView
                            .padding(.top, infoHeaderReservedHeight + 8)
                            .padding(.trailing, 8)
                    }
                    Spacer()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            #if os(tvOS)
            .focusScope(searchFocusNamespace)
            .onExitCommand(perform: dismissTextSearchOverlay)
            #endif
            .zIndex(3)
        }
    }

    var isPad: Bool {
        PlatformAdapter.isPad
    }

    var isPhone: Bool {
        PlatformAdapter.isPhone
    }

    var isPhonePortrait: Bool {
        #if os(iOS)
        return isPhone && verticalSizeClass == .regular
        #else
        return false
        #endif
    }

    var isTV: Bool {
        PlatformAdapter.isTV
    }

    var isShortcutHelpVisible: Bool {
        isShortcutHelpPinned || isShortcutHelpModifierActive
    }

    @ViewBuilder
    func menuOverlay(for chunk: InteractiveChunk) -> some View {
        if isMenuVisible {
            VStack(alignment: .leading, spacing: 12) {
                menuDragHandle
                if let summary = viewModel.highlightingSummary {
                    Text(summary)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                controlBar(chunk)
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(menuBackground)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .shadow(color: Color.black.opacity(0.25), radius: 12, x: 0, y: 6)
            .transition(.move(edge: .top).combined(with: .opacity))
            .accessibilityAddTraits(.isModal)
            .zIndex(2)
        }
    }

}
