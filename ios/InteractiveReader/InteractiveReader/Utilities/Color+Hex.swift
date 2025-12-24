import Foundation
import SwiftUI

extension Color {
    init?(hex: String) {
        let trimmed = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.hasPrefix("#") else { return nil }
        let hexString = String(trimmed.dropFirst())
        guard hexString.count == 6 else { return nil }
        let scanner = Scanner(string: hexString)
        var value: UInt64 = 0
        guard scanner.scanHexInt64(&value) else { return nil }
        let red = Double((value & 0xFF0000) >> 16) / 255.0
        let green = Double((value & 0x00FF00) >> 8) / 255.0
        let blue = Double(value & 0x0000FF) / 255.0
        self.init(red: red, green: green, blue: blue)
    }
}
