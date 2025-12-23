import SwiftUI

// A small wrapper to provide a consistent container across platforms.
public struct PlatformGroupBox<Label: View, Content: View>: View {
    private let label: () -> Label
    private let content: () -> Content

    public init(@ViewBuilder label: @escaping () -> Label, @ViewBuilder content: @escaping () -> Content) {
        self.label = label
        self.content = content
    }

    public var body: some View {
        #if os(tvOS)
        VStack(alignment: .leading, spacing: 8) {
            label()
                .font(.headline)
            content()
        }
        .padding(12)
        .background(Color.secondary.opacity(0.15))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        #else
        GroupBox(label: label(), content: content)
        #endif
    }
}

public extension PlatformGroupBox where Label == EmptyView {
    init(@ViewBuilder content: @escaping () -> Content) {
        self.init(label: { EmptyView() }, content: content)
    }
}

#Preview("PlatformGroupBox") {
    PlatformGroupBox(label: { Text("Example") }) {
        VStack(alignment: .leading) {
            Text("Content line 1")
            Text("Content line 2")
        }
        .padding(.vertical, 4)
    }
    .padding()
}
