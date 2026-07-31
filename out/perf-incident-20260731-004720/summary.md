Symptom: Pi still feels janky with the cmux extension enabled.
User impact: Interactive prompt submission and rendering feel slower than `pi -ne`.
Source: User dogfood report after PR 9289.
Target surface: macOS tagged cmux app, Pi 0.82.1.
Build/version/tag: cmux b2e2deeecb, tag pilag.
Repro workload: Matched fresh `pi` and `pi -ne` sessions, identical prompt and tool flow.
Expected bad behavior: Extension-enabled Pi shows longer prompt-submit latency or visible frame stalls.

Owner: cmux-managed Pi extension event handlers.
Invariant: Hook telemetry must not delay Pi input, model start, or terminal rendering.
Current hypothesis: `before_agent_start` awaits the cmux command subprocess before Pi starts the agent.
Proof needed: Matched timing and frame evidence for `pi` versus `pi -ne`, followed by the same comparison after any fix.
