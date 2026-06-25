import SwiftUI
#if os(iOS)
import UIKit
#endif

struct TokenWordView: View {
    let text: String
    let color: Color
    let isSelected: Bool
    let isShadowSelected: Bool
    let isPlaybackSelected: Bool
    let isPlaybackShadowSelected: Bool
    let horizontalPadding: CGFloat
    let verticalPadding: CGFloat
    let cornerRadius: CGFloat
    let onTap: ((Bool) -> Void)?
    let onLookup: (() -> Void)?

    var body: some View {
        let isPrimaryHighlight = isSelected || isPlaybackSelected
        let isShadowHighlight = !isPrimaryHighlight && (isShadowSelected || isPlaybackShadowSelected)
        Text(text)
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .allowsTightening(true)
            .padding(.horizontal, horizontalPadding)
            .padding(.vertical, verticalPadding)
            .foregroundStyle(isPrimaryHighlight ? TextPlayerTheme.selectionText : color)
            .background(
                Group {
                    if isPrimaryHighlight || isShadowHighlight {
                        RoundedRectangle(cornerRadius: cornerRadius)
                            .fill(isPrimaryHighlight ? TextPlayerTheme.selectionGlow : TextPlayerTheme.selectionShadow)
                    }
                }
            )
            #if !os(tvOS)
            .gesture(tokenTapGesture)
            #endif
            #if os(iOS)
            .contextMenu {
                Button("Look Up") {
                    DictionaryLookupPresenter.show(term: text)
                }
                Button("Copy") {
                    UIPasteboard.general.string = text
                }
            }
            #endif
    }

    #if !os(tvOS)
    private var tokenTapGesture: some Gesture {
        let doubleTap = TapGesture(count: 2)
            .onEnded {
                onTap?(false)
                onLookup?()
            }
        let singleTap = TapGesture(count: 1)
            .onEnded { onTap?(true) }
        return doubleTap.exclusively(before: singleTap)
    }
    #endif
}

#if os(iOS)
enum DictionaryLookupPresenter {
    static func show(term: String) {
        let trimmed = term.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        let controller = UIReferenceLibraryViewController(term: trimmed)
        guard let presenter = topViewController() else { return }
        presenter.present(controller, animated: true)
    }

    private static func topViewController() -> UIViewController? {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        let windows = scenes.flatMap { $0.windows }
        let root = windows.first(where: { $0.isKeyWindow })?.rootViewController
        return topViewController(from: root)
    }

    private static func topViewController(from root: UIViewController?) -> UIViewController? {
        if let presented = root?.presentedViewController {
            return topViewController(from: presented)
        }
        if let navigation = root as? UINavigationController {
            return topViewController(from: navigation.visibleViewController)
        }
        if let tab = root as? UITabBarController {
            return topViewController(from: tab.selectedViewController)
        }
        return root
    }
}
#endif
