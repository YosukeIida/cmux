Symptom: Significant lag while Pi runs with the cmux session extension enabled.
User impact: Pi interactions pause while extension event handlers execute.
Source: User report plus local Pi 0.82.1 installation.
Target surface: macOS terminal, Pi extension, and cmux CLI hook bridge.
Build/version/tag: cmux origin/main 541fe7f0c7; installed Pi 0.82.1; dogfood tag pilag.
Repro workload: Compare fixed Pi lifecycle/tool-event traffic with and without the cmux extension, then isolate extension handler costs.
Expected bad behavior: Extension work adds measurable synchronous or awaited latency to high-frequency Pi events.

Owner: Pending runtime attribution.
Invariant: High-frequency Pi event handlers must not block Pi interaction on cmux IPC or repeated process discovery.
Why the old path failed: Pending runtime attribution.
Fix shape: Pending runtime attribution.
Proof that closes it: Same fixed workload before and after, plus behavioral regression coverage.
