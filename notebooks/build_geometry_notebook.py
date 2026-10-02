"""Build an executed, artifact-only explanation of the geometry experiment."""
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient
root=Path(__file__).resolve().parents[1]
nb=nbf.v4.new_notebook();nb.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
nb.cells=[md('''# Does putting more pixels on the board help?

PCB1 development comparison, October2,2026. The original result is preserved.
C1 uses a conservative content-derived crop with aspect preservation at256 pixels;
C2 repeats that geometry at512. Both retain frozen ResNet18 and4096 uniformly
sampled normal patches. No training or PCB2 evaluation occurred.

This notebook reads saved tables/charts only. It does not run inference, refit a
reference bank or select a threshold. Full interpretation and limitations are in
`artifacts/pcb1_geometry_comparison/findings.md`.'''),code('''from pathlib import Path
import json,hashlib
import pandas as pd
from IPython.display import display,Image
root=Path.cwd()
if not (root/'artifacts').exists():root=root.parent
folder=root/'artifacts/pcb1_geometry_comparison'
meta=json.loads((folder/'comparison_metadata.json').read_text())
for name,expected in meta['outputs'].items():
 assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==expected
for size in [256,512]:
 review=json.loads((root/f'artifacts/runs/geometry_{size}_v1/independent_review.json').read_text())
 assert review['passed']
print('Saved comparison tables/charts verified; both independent reviews passed.')'''),md('''## The geometry check came first

The rule finds a large connected blue area and adds space around its sides and
connector ends. It falls back to the whole image if the region is implausible.
It is designed specifically for these blue PCB1 boards. It does not rotate or
register boards. The audit checked all904 fitting/calibration normals; visual
review covered14 systematic examples including crop-size extremes.'''),code('''audit=json.loads((root/'artifacts/pcb1_geometry/audit.json').read_text())
display(pd.DataFrame([{'normal_count':audit['normal_count'],'fallback_count':audit['fallback_count'],'median_crop_fraction':audit['crop_area_quantiles']['0.5'],'visual_samples':len(audit['selection_ids'])}]))
display(Image(filename=str(root/'artifacts/pcb1_geometry/normal_contact_sheet_03.png')))'''),md('''## Compare all three recipes

Thresholds are separately calibrated from the same181 normal boards under the
original95th/99th quantile policy. Recall and false alarms must be read together.
A retrospective A2 threshold was never substituted. Pixel AP describes ranking;
it is not detection probability. The median reflects a typical anomalous image,
whereas pooled AP can be dominated by large easy defects.'''),code('''display(pd.read_csv(folder/'comparison.csv'))
display(Image(filename=str(folder/'comparison.png')))
display(pd.read_csv(folder/'type_recall_comparison.csv'))
display(Image(filename=str(folder/'type_recall.png')))'''),md('''## Resources and geometry failures

Fixed4096 memory means lower patch coverage at512. Sampling is uniform, not a
coreset. Streamed extraction avoids allocating a full raw fitting feature bank.
Times below include source hashing in the new runs; original published latency
excluded raw hashing. Do not treat their difference as a perfectly matched timing
benchmark. Full-image evaluation keeps pixels outside the crop; their score is zero.
Any ground truth cropped out is still counted and reported.'''),code('''rows=[]
for size in [256,512]:
 p=root/f'artifacts/runs/geometry_{size}_v1'
 runtime=json.loads((p/'normal_runtime.json').read_text());bank=json.loads((p/'memory_metadata.json').read_text());m=json.loads((p/'metrics.json').read_text())
 rows.append({'size':size,'memory_fraction':bank['fraction'],'memory_count':bank['count'],**runtime,**m['geometry']})
display(pd.DataFrame(rows))'''),md('''## Same examples, side by side

The eleven example IDs were fixed in A2 before these experiments. All maps are
shown in the same full-image256 view. Cyan is the source annotation. The display
shows map divided by that recipe's pixel threshold on a shared0–2 scale; this is
for comparison only and does not change any metric or imply probability.'''),code('''display(pd.read_csv(folder/'qualitative_selection.csv'))
for page in sorted(folder.glob('contact_sheet_*.png')):display(Image(filename=str(page)))'''),md('''## What this comparison can establish

C1 measures the complete crop/aspect/padding block relative to the original direct
resize. C2 measures resolution under a fixed reference count and reduced coverage.
Neither comparison isolates every preprocessing effect. Source pose is unchanged.
PCB1 has already guided development, so these are development findings. A complete
selected recipe must be frozen before fresh-category PCB2 confirmation.''')]
nbf.validate(nb)
NotebookClient(nb,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(root)}}).execute()
nbf.write(nb,root/'notebooks/pcb1_geometry_resolution.ipynb')
print('Executed geometry/resolution notebook')
