The SRD’s main weakness is that it stops one level short of “infrastructure defensibility”: while the modules
and use cases show what the system intends to do, the report does not sufficiently justify how the
infrastructure behaves under realistic constraints, i.e. trust boundaries, threat
model depth, performance (simulation + device management + IDS + attack simulation + dashboard),
which raises feasibility risk unless the minimum viable deliverable is clearly prioritized and evaluation
metrics are defined early.
SDG alignment is present and relevant but should be strengthened by mapping SDG 4 to concrete outcomes
and indicators.
Corrections Needed / Required Revisions (SRD):
1. Define measurable success metrics (e.g., detection accuracy/latency, dashboard refresh latency, max
simulated nodes, resource usage thresholds).
2. Add an explicit threat model + trust boundaries (what is trusted, what is hostile, where inspection
happens, what attacks are in-scope/out-of-scope).
3. Clarify feasibility via MVP prioritization (what MUST work by end of Semester 1 vs “nice-to-have”).
4. Strengthen evaluation plan (test cases + expected results + pass/fail criteria tied directly to objectives).
5. Improve SDG mapping (link SDG 4 to system features + measurable education impact indicators, not
only narrative).
The presentation is clear but remains largely descriptive, with limited technical justification of Computing
Infrastructure design decisions. Key aspects such as traffic flow, trust boundaries, and evaluation readiness are
not sufficiently explained