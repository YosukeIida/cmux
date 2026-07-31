import CmuxTerminal

/// Preserves Ghostty manual-I/O order while crossing to the tmux main-actor owner.
final class RemoteTmuxPaneInputForwarder: Sendable {
    private let continuation: AsyncStream<TerminalManualInput>.Continuation
    private let consumer: Task<Void, Never>

    @MainActor
    init(onInput: @escaping @MainActor @Sendable (TerminalManualInput) -> Void) {
        // Terminal input is a lossless stream: a bounded AsyncStream policy
        // would silently remove a keystroke. The prior Task-per-callback bridge
        // was also unbounded; downstream SSH writes retain their byte budget and
        // reconnect on overflow.
        let (stream, continuation) = AsyncStream.makeStream(
            of: TerminalManualInput.self,
            bufferingPolicy: .unbounded
        )
        self.continuation = continuation
        self.consumer = Task { @MainActor in
            for await input in stream {
                onInput(input)
            }
        }
    }

    deinit {
        continuation.finish()
        consumer.cancel()
    }

    /// Adds one event from Ghostty's serial manual-I/O callback.
    func send(_ input: TerminalManualInput) {
        continuation.yield(input)
    }
}
