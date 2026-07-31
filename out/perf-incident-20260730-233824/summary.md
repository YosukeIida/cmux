Symptom: Significant lag while Pi runs with the cmux session extension enabled.
User impact: Pi interactions pause while extension event handlers execute.
Source: User report plus local Pi 0.82.1 installation.
Target surface: macOS terminal, Pi extension, and cmux CLI hook bridge.
Build/version/tag: cmux origin/main 541fe7f0c7; installed Pi 0.82.1; dogfood tag pilag.
Repro workload: Compare fixed Pi lifecycle/tool-event traffic with and without the cmux extension, then isolate extension handler costs.
Expected bad behavior: Extension work adds measurable synchronous or awaited latency to high-frequency Pi events.

Before evidence: The installed managed extension imports spawnSync. The existing dispatch responsiveness harness failed after 5.60 seconds with two serialized, fully blocked prompt-submit calls.
Bundled-source control: The same harness against current main's generated asynchronous source passed in 237 ms.
Live sample: live-pi-before.sample.txt shows the idle Pi process sleeping in its Node event loop, so the reported cost is event-triggered rather than sustained CPU.

Owner: The cmux CLI owns the generated Pi extension at the managed marker boundary.
Invariant: A cmux-managed Pi extension must advance to the source bundled with the cmux CLI without requiring users to remember another setup command.
Why the old path failed: cmux upgraded its bundled extension to asynchronous dispatch, but existing generated files were only replaced by a manual `cmux hooks setup`; the local Pi process kept loading the older synchronous file.
Fix shape: On Pi session-start, refresh an existing marker-owned extension atomically when its content differs. Missing or user-owned files remain untouched, and refresh failure never blocks hook delivery.
Proof that closes it: The regression invokes Pi session-start with a stale marker-owned fixture and requires the bundled source to replace it, then the same dispatch harness must pass against that refreshed source.

Final proof:
- `test_pi_extension_install.py`: PASS against the `pilag` CLI.
- `test_pi_extension_dispatch.py`: PASS against the `pilag` CLI.
- Focused responsiveness workload: PASS in 529 ms against `pilag`, versus 5.60 seconds and failure with the installed stale source.
