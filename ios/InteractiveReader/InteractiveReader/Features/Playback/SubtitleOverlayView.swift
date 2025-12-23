import SwiftUI

struct SubtitleOverlayView: View {
    let cues: [SubtitleCue]
    let currentTime: Double

    var body: some View {
        if let cue = activeCue {
            Text(cue.text)
                .font(.title3)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(.black.opacity(0.6), in: RoundedRectangle(cornerRadius: 12))
                .foregroundStyle(.white)
                .padding(.bottom, 24)
                .frame(maxWidth: .infinity)
                .transition(.opacity)
        }
    }

    private var activeCue: SubtitleCue? {
        cues.last { currentTime >= $0.start && currentTime <= $0.end }
    }
}
