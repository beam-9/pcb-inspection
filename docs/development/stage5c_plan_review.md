# Stage 5C handoff evaluation

Accepted as a controlled post-confirmation PCB2 development experiment. Primary comparison is historical D2 versus the exact Stage 5B wrapper at512; D1/D2 differences prohibit resolution-only attribution. D2 bank, threshold calibration, reference ordering, crop and score implementation remain frozen. The wrapper is imported from Stage5B without edits.

Operational clarifications before inference:
- Common256 metrics and original source GT remain the matched localization denominator. Native512 grid counts are separate.
- Strong support requires5/5 detection, recovery of the Stage5B lost case, broad burden reduction across cases and exact195 no-ops. No arbitrary numerical efficacy cutoff or result-driven recipe changes.
- Full freeze binds current uncommitted history as file hashes, not merely HEAD. Stage5B history navigation snapshots resolve older Stage5A bindings; Stage5C snapshots preserve current navigation before publication updates.
- Preexperiment four-signal context is saved before inference and never used to tune.
- Timing separates decoding, geometry, pose, tensor preparation, features, and frozen scoring. Scoring includes historical inverse mapping; additional source/common inverse timers include inverse rotation. Separately instrumenting inside the frozen wrapper would change its identity, so that nested cost is disclosed.
- Independent verification uses separate pixel/grid calculations and manually constructed RGB letterboxes plus float64 SciPy distances for five reversed inputs. This is computational independence, not review by a separate person.
- n=5, no reversed normals, exposed PCB2, union GT and unknown physical board identities limit interpretation. Keep original historical portfolio primary and choose a next question only from completed evidence.
