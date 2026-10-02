"""Execute a portable A2 evidence-reading notebook; no raw data or inference needed."""
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient
root=Path(__file__).resolve().parents[1]
md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
nb=nbf.v4.new_notebook();nb.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
nb.cells=[md('''# PCB1 A2: explain the misses before changing the detector

## Findings

Scratch and melt are the weakest source-labeled groups. The largest annotation quartile is easier than the smaller groups. Retrospective threshold movement can recover 10 additional anomalies with the same nine observed false alarms, but misses also have poor localization. Normal-score shift and cross-location matching are not established causes.

**PCB1 is development data.** This notebook reads the saved A2 tables and charts; it does not run a detector or select an operational threshold. The first pilot is preserved and PCB2 remains sealed. See `artifacts/pcb1_a2/diagnostic_summary.md` for the seven diagnostic questions and `docs/improvement_plan_review.md` for corrections to the proposed plan.'''),
code('''from pathlib import Path
import json,hashlib
import pandas as pd
from IPython.display import display,Image,Markdown
root=Path.cwd()
if root.name=='notebooks':root=root.parent
folder=root/'artifacts/pcb1_a2'
metadata=json.loads((folder/'diagnostics_metadata.json').read_text())
for name,expected in metadata['outputs'].items():
    assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==expected
verification=json.loads((folder/'verification_a2.json').read_text())
assert verification['passed'] and verification['no_model_inference']
print('Original run:',metadata['run_id'],'; anomaly images:',metadata['anomaly_images'],'; multi-label images:',metadata['multi_label_images'])'''),
md('''## Threshold placement and ranking

These are retrospective **best attainable** operating points within an FPR budget, chosen from all saved labeled PCB1 scores. Tied scores enter together, using strict `score > threshold`. They are not normal-only calibrated settings or fresh validation. The original operating point is 43/100 anomalies and 9/100 normal false alarms.'''),
code('''operating=pd.read_csv(folder/'recall_vs_fpr.csv')
display(operating.round(5))
display(Image(filename=str(folder/'recall_vs_fpr.png')))'''),
md('''## Source defect labels and localization

Nine multi-label images contribute to 110 memberships. An image appears once in every named source group. Localization uses its union mask, so a grouped value is not the isolated quality of a specific component defect. “Missing” performs substantially better than “scratch” and “melt” in this run.'''),
code('''types=pd.read_csv(folder/'recall_by_defect_type.csv')
display(types[['defect_type','sample_count','detected_count','missed_count','recall','median_per_image_pixel_ap','peak_inside_mask_rate']].round(4))
display(Image(filename=str(folder/'recall_by_defect_type.png')))
display(Image(filename=str(folder/'pixel_ap_by_defect_type.png')))'''),
md('''## Annotation size

Quartile boundaries retain equal-area ties together, giving 27/24/25/24 images. Geometry is the original 256-square mask/map resolution. Association between size and score does not isolate resize loss from defect type, memory coverage or feature sensitivity.'''),
code('''quartiles=pd.read_csv(folder/'recall_by_defect_size_quartile.csv')
display(quartiles.round(5))
display(Image(filename=str(folder/'recall_by_defect_size_quartile.png')))
display(Image(filename=str(folder/'score_vs_defect_area.png')))'''),
md('''## Normal-score uncertainty

Calibration scores have somewhat lower observed medians/tails. With 100 test normals, 9 false alarms give a Wilson 95% interval of approximately 4.8–16.2% under independent-image assumptions; physical-object independence remains unverified. The KS result does not establish a shift and also does not prove equivalence. Finite normal calibration adds uncertainty to the threshold itself.'''),
code('''display(pd.read_csv(folder/'normal_score_distribution.csv').round(5))
display(Image(filename=str(folder/'normal_score_distribution.png')))
uncertainty=json.loads((folder/'association_uncertainty.json').read_text())
display(pd.DataFrame(uncertainty['detection_localization_groups']).round(4))
print('Observed KS distance:',round(uncertainty['calibration_test_normal_ks']['statistic'],4))'''),
md('''## Saved nearest-reference locations

Offsets come from maximum-score query patches on an **unregistered** 32-square feature grid. A missed defect may be elsewhere than that winning patch; source rotation and translation can also produce offsets. Larger offsets occur in 15/57 misses versus 19/43 true positives, so the saved traces do not prioritize spatial restriction as the first fix.'''),
code('''display(pd.read_csv(folder/'trace_by_outcome.csv').round(4))'''),
md('''## Systematic qualitative review

Selection rules include strong/weak-localized true positives, just-below/low-score misses, the smallest area quartile, every source type, and representative normal false positives. Selection IDs and reasons are saved. Raw map scale and original thresholds are shared. Cyan contours are retrospective source masks.'''),
code('''display(pd.read_csv(folder/'qualitative/selection.csv'))
for page in sorted((folder/'qualitative').glob('contact_sheet_*.png')):
    display(Image(filename=str(page)))'''),
md('''## Next bounded experiments

First validate a fitting-normal-derived board crop, aspect preservation, orientation and inverse transforms. Then isolate geometry at 256 and resolution at 512 with the same ResNet18/memory/scoring/normal-calibration rule. Compare coreset selection at matched counts before increasing memory or replacing the backbone. The naive WideResNet 512 feature bank exceeds the current RAM budget; use an explicit resource smoke and cap.

These candidates have not been executed and no performance gain is claimed. Registration is a testable prerequisite for spatial matching, not a guaranteed improvement. Freeze the full selected recipe before the first PCB2 confirmation; category-specific normal fitting is not zero-shot transfer.''')]
nbf.validate(nb)
NotebookClient(nb,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(root)}}).execute()
nbf.write(nb,root/'notebooks/pcb1_a2_diagnostics.ipynb')
print('Executed A2 evidence notebook')
