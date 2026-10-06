# Stage6A findings

Completed detector-neutral diagnosis of36 fixed PCB2 development anomalies. Six canonical missing-label misses and eight fixed R1/R2 misses overlap across nine distinct images. Seven of nine misses have native GT rank1; the remaining ranks are2 and12. Image scores are0.63–8.26% below the frozen D2 threshold. GT query distances are lower on misses; canonical missing-hit controls overlap, while selected small-case image medians separate. Causes and intervention benefit remain unresolved.

Decision gate: proposal Branch D, recommend freezing the existing D2+orientation candidate with limitations rather than forcing Stage6B. Formalv1.0 model freeze, receipt and UI are pending. No detector changes or new detection decisions occurred.

See the [full journey chapter](../../docs/journey/stage_06_final_model_selection.md), [reviewed proposal](../../docs/development/stage6a_plan_review.md), [case diagnosis](case_diagnosis.csv), [full per-recipe diagnostics](per_recipe_diagnostics.csv), [feature distances](feature_distance.csv), [patch ranks](patch_rank_diagnostics.csv), [aggregation](aggregation_diagnostics.csv), [decision gate](decision_gate.json), [computational audit](independent_review.json) and [artifact-only notebook](../../notebooks/pcb2_stage6a_diagnosis.ipynb). Ten exported figures cover all eight requested types, including every target miss.
