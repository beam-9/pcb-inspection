# Pose diagnostic findings

Post-confirmation PCB2 development diagnosis. Labels were finalized from image-only cues before this outcome join. Prior Stage4 visual knowledge remains acknowledged.

D1: reversed5 images contribute 28.8% of all FP pixels; medianFP 29180 vs canonical 1216. Median anomaly pixelAP 0.076 vs canonical 0.333; reversed recall 100%.
D2: reversed5 images contribute 29.8% of all FP pixels; medianFP 19367 vs canonical 938. Median anomaly pixelAP 0.274 vs canonical 0.515; reversed recall 100%.

All1001 normals are canonical, so reversed-normal false-alarm behavior is unestimable. The5uncertain cases have canonical-looking layouts with damaged/absent pin cues; they remain uncertain and are not evidence of180-degree reversal. Small reversed n, defect confounding and already-exposed data prevent a causal pose claim. Registration has not been tested.

False-positive counts are union minus ground-truth mask area; predicted-positive counts add intersection. All200 saved image IDs and pooled intersection/union denominators match frozen Stage4 results. No detector was run.
