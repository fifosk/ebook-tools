import SwiftUI

struct BrowseListRowFrameCapture: View {
    let coordinateSpaceName: String

    var body: some View {
        #if os(iOS)
        GeometryReader { proxy in
            Color.clear.preference(
                key: BrowseListRowFramePreferenceKey.self,
                value: [proxy.frame(in: .named(coordinateSpaceName))]
            )
        }
        #else
        Color.clear
        #endif
    }
}

extension View {
    @ViewBuilder
    func browseListCollapseInteraction(
        rowFrames: Binding<[CGRect]>,
        coordinateSpaceName: String,
        onCollapse: (() -> Void)?
    ) -> some View {
        #if os(iOS)
        self
            .coordinateSpace(name: coordinateSpaceName)
            .onPreferenceChange(BrowseListRowFramePreferenceKey.self) { frames in
                rowFrames.wrappedValue = frames
            }
            .simultaneousGesture(
                DragGesture(minimumDistance: 24, coordinateSpace: .named(coordinateSpaceName))
                    .onEnded { value in
                        handleBrowseListCollapseDrag(
                            value,
                            rowFrames: rowFrames.wrappedValue,
                            onCollapse: onCollapse
                        )
                    }
            )
        #else
        self
        #endif
    }

    #if os(iOS)
    private func handleBrowseListCollapseDrag(
        _ value: DragGesture.Value,
        rowFrames: [CGRect],
        onCollapse: (() -> Void)?
    ) {
        guard let onCollapse else { return }
        let start = value.startLocation
        guard !rowFrames.contains(where: { $0.contains(start) }) else { return }
        let horizontal = value.translation.width
        let vertical = value.translation.height
        guard abs(horizontal) > abs(vertical) else { return }
        guard horizontal < -70 else { return }
        guard abs(vertical) < 50 else { return }
        onCollapse()
    }
    #endif
}

#if os(iOS)
private struct BrowseListRowFramePreferenceKey: PreferenceKey {
    static var defaultValue: [CGRect] = []

    static func reduce(value: inout [CGRect], nextValue: () -> [CGRect]) {
        value.append(contentsOf: nextValue())
    }
}
#endif
