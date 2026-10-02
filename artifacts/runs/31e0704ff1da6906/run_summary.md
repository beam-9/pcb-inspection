# Frozen Phase A run 31e0704ff1da6906

Recommendation: **stop/revise methodology**. Primary image AP 0.8516, AUROC 0.8654,
recall 43/100 anomalies, false alarms 9/100 normals. Baseline AP 0.8276, AUROC 0.7872,
same recall and 2/100 false alarms. Pooled pixel AP 0.7920 and global pixel IoU 0.1218
hide uneven small-region localization: supplemental median per-anomaly AP 0.0393,
map peak inside annotation for 26/100 anomalies. CPU warm median 0.3069s, p95 0.3355s.

The original final artifacts are hash-recorded in final_complete.json; verification.json
independently confirms arithmetic and sampled numerical patch traces. No settings changed
or final scoring rerun. See docs/pilot_findings.md and notebooks/pcb1_pilot.ipynb at repo root.
