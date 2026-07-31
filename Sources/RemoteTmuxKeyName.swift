import Carbon.HIToolbox
import GhosttyKit

/// A tmux key name whose spelling is safe to place in a `send-keys` command.
///
/// Physical remote-mirror keys retain their identity until tmux translates them
/// for the pane. Literal text never becomes a ``RemoteTmuxKeyName`` and continues
/// through the binary-safe `send-keys -H` path.
nonisolated struct RemoteTmuxKeyName: Equatable, Sendable {
    let value: String

    /// Resolves navigation and function keys whose local xterm encoding can
    /// disagree with the remote pane's tmux terminfo and terminal modes.
    init?(inputEvent: ghostty_input_key_s) {
        guard inputEvent.action == GHOSTTY_ACTION_PRESS
                || inputEvent.action == GHOSTTY_ACTION_REPEAT,
              !inputEvent.composing else {
            return nil
        }

        let base: String
        switch Int(inputEvent.keycode) {
        case kVK_Home: base = "Home"
        case kVK_End: base = "End"
        case kVK_Help: base = "IC"
        case kVK_ForwardDelete: base = "DC"
        case kVK_PageUp: base = "PPage"
        case kVK_PageDown: base = "NPage"
        case kVK_UpArrow: base = "Up"
        case kVK_DownArrow: base = "Down"
        case kVK_LeftArrow: base = "Left"
        case kVK_RightArrow: base = "Right"
        case kVK_F1: base = "F1"
        case kVK_F2: base = "F2"
        case kVK_F3: base = "F3"
        case kVK_F4: base = "F4"
        case kVK_F5: base = "F5"
        case kVK_F6: base = "F6"
        case kVK_F7: base = "F7"
        case kVK_F8: base = "F8"
        case kVK_F9: base = "F9"
        case kVK_F10: base = "F10"
        case kVK_F11: base = "F11"
        case kVK_F12: base = "F12"
        default: return nil
        }

        // AppKit sometimes supplies the private-use function-key character
        // even though this is still a physical, non-text key. Reject real text
        // so an IME commit can never be replaced by a tmux key command.
        if let textPointer = inputEvent.text {
            let text = String(cString: textPointer)
            if !text.isEmpty {
                guard text.unicodeScalars.count == 1,
                      let scalar = text.unicodeScalars.first,
                      (0xF700...0xF8FF).contains(scalar.value) else {
                    return nil
                }
            }
        }

        let rawModifiers = inputEvent.mods.rawValue
        guard rawModifiers & GHOSTTY_MODS_SUPER.rawValue == 0 else { return nil }
        var modifiers: [String] = []
        modifiers.reserveCapacity(3)
        if rawModifiers & GHOSTTY_MODS_CTRL.rawValue != 0 { modifiers.append("C") }
        if rawModifiers & GHOSTTY_MODS_ALT.rawValue != 0 { modifiers.append("M") }
        if rawModifiers & GHOSTTY_MODS_SHIFT.rawValue != 0 { modifiers.append("S") }
        value = (modifiers + [base]).joined(separator: "-")
    }

    /// Resolves a CLI/socket key spelling to tmux's canonical key name.
    init?(rawName: String) {
        let normalized = rawName.lowercased().replacingOccurrences(of: "+", with: "-")
        switch normalized {
        case "enter", "return": value = "Enter"; return
        case "tab": value = "Tab"; return
        case "escape", "esc": value = "Escape"; return
        case "backspace": value = "BSpace"; return
        case "shift-tab", "backtab": value = "BTab"; return
        case "space": value = "Space"; return
        case "sigint": value = "C-c"; return
        case "eof": value = "C-d"; return
        case "sigtstp": value = "C-z"; return
        case "sigquit": value = "C-\\"; return
        default: break
        }

        let parts = normalized.split(separator: "-").map(String.init)
        guard let rawBase = parts.last else { return nil }
        let base: String
        if rawBase.count == 1,
           let byte = rawBase.utf8.first,
           (byte >= 48 && byte <= 57) || (byte >= 97 && byte <= 122) {
            base = rawBase
        } else if rawBase.first == "f",
                  let number = Int(rawBase.dropFirst()),
                  (1...12).contains(number) {
            base = "F\(number)"
        } else {
            switch rawBase {
            case "home": base = "Home"
            case "end": base = "End"
            case "insert", "ic": base = "IC"
            case "delete", "del", "dc", "forward_delete": base = "DC"
            case "pageup", "page_up", "pgup", "ppage": base = "PPage"
            case "pagedown", "page_down", "pgdn", "npage": base = "NPage"
            case "up", "arrow_up", "arrowup": base = "Up"
            case "down", "arrow_down", "arrowdown": base = "Down"
            case "left", "arrow_left", "arrowleft": base = "Left"
            case "right", "arrow_right", "arrowright": base = "Right"
            default: return nil
            }
        }

        var hasControl = false
        var hasMeta = false
        var hasShift = false
        for modifier in parts.dropLast() {
            switch modifier {
            case "c", "ctrl", "control": hasControl = true
            case "m", "alt", "opt", "option": hasMeta = true
            case "s", "shift": hasShift = true
            default: return nil
            }
        }

        var modifiers: [String] = []
        modifiers.reserveCapacity(3)
        if hasControl { modifiers.append("C") }
        if hasMeta { modifiers.append("M") }
        if hasShift { modifiers.append("S") }
        value = (modifiers + [base]).joined(separator: "-")
    }
}
