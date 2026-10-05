"""Build/execute saved-artifact diagnostic evidence; never run the detector."""
from pathlib import Path
import argparse
import nbformat as nbf
from nbclient import NotebookClient


def build(root,execute):
 root=Path(root).resolve()
 if (root/'artifacts/stage5a/diagnostics.json').exists():raise FileExistsError('Preserve completed notebook; reproduce in separate workspace')
 md,code=nbf.v4.new_markdown_cell,nbf.v4.new_code_cell
 notebook=nbf.v4.new_notebook();notebook.metadata.kernelspec={'display_name':'Python3','language':'python','name':'python3'}
 notebook.cells=[md('''# Stage 5A: diagnose PCB2 before changing the detector

This is post-confirmation development diagnosis. Stage4 was committed/pushed as
2ec21c4; its original predictions, code and model banks remain unchanged. This
notebook reads saved diagnostic tables, figures and receipts. It performs no raw
image access, feature extraction, fitting, scoring, threshold tuning or networking.

The strongest first intervention candidate is canonical orientation normalization,
not yet tested. Reversed boards have broad maps, but do not explain image-level
misses here. Canonical missing-label misses retrieve local references, weakening
the proposed distant-match explanation. Read these as associations, not causes.'''),
 code('''from pathlib import Path
import hashlib,json,io
import pandas as pd
from PIL import Image as PILImage
from IPython.display import display,Image,Markdown
root=Path.cwd()
if not (root/'artifacts').is_dir():root=root.parent
base=root/'artifacts/stage5a'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def table(name):return pd.read_csv(base/name)
def show(name):
    with PILImage.open(base/name) as im:
        im.thumbnail((1000,1800));buf=io.BytesIO();im.save(buf,format='PNG')
    display(Image(data=buf.getvalue()))
metadata=json.loads((base/'report_metadata.json').read_text())
assert metadata['new_detector_inference'] is False
for field in ['sources','outputs']:
    for name,expected in metadata[field].items():
        assert sha(root/name)==expected,name
review=json.loads((base/'independent_review.json').read_text())
assert review['passed']
frame=table('combined/per_image_diagnostics.csv')
assert len(frame)==200 and frame.image_id.is_unique
assert frame.missing_component.sum()==19
print('Verified saved report identities and diagnostic grain.')'''),
 md('''## Pose: compare anomalies with anomalies

The image-only pin classifier labeled1,101 images before outcome joins. All1,001
normals are canonical. Among100 anomalies,90 canonical,5 reversed,5 uncertain.
Uncertain images visually have canonical layouts with damaged connector cues;
do not combine them with reversed poses. PriorStage4 knowledge exists, so this
is not retrospectively double-blind. No reversed normals means no reversed FPR.
The main FP comparison uses90/5/5 anomalies, not pooled canonical normals.'''),
 code('''display(table('pose/pose_population.csv'))
display(table('pose/pose_binary_stratified_summary.csv').round(4))
show('pose/pose_fp_pixels_anomalies.png')
show('pose/pose_pixel_ap.png')
show('pose/pose_contact_sheet.png')'''),
 md('''## Missing labels: frozen top-five references

All19 missing-labeled cases, both resolutions, all mask-overlap grid footprints
and a one-cell context ring were traced:3,698 queries/18,490 pairs. No spatial
restriction was applied. Radii0.05/0.10/0.20 are crop-diagonal units, not tuned.
Union GT on two multi-type images cannot isolate a particular missing component;
grid-cell footprints are not the full ResNet receptive field. Image-weighted
summaries avoid letting larger defects contribute more rows to group medians.
The30-pair bounded center-context visual review is not a prevalence estimate.'''),
 code('''cases=table('missing_component/missing_cases.csv')
trace=table('missing_component/nn_trace.csv')
assert len(cases)==19 and len(trace)==18490
assert trace.groupby(['query_image_id','size','query_id']).size().eq(5).all()
display(cases[['image_id','pose_label','outcome_group','d1_pixel_ap','d2_pixel_ap','d1_nn_spatial_median','d2_nn_spatial_median']].round(4))
display(table('missing_component/group_summary.csv').query("query_set=='defect_overlap'").round(4))
show('missing_component/missing_hit_vs_miss.png')
show('missing_component/cross_location_fraction.png')
display(table('missing_component/selected_reference_context_review.csv')[['query_image_id','size','neighbor_rank','context_label','review_status']])'''),
 md('''## Broad maps and small defects

The4×4 grid is normalized crop content with letterbox padding excluded. Conservative
crop background remains; cells are not registered anatomical zones. Common256
counts and native-content spread have different explicit denominators. Fixed color
scales permit within-recipe panel comparisons. Pixel evidence, patch-max image
flags and competing responses are kept separate. Operational small-defect categories
can overlap and do not prove representation failure. D2 differs in normal calibration
and candidate population as well as resolution.'''),
 code('''maps=table('broad_maps/map_spread.csv')
assert maps.groupby('recipe').size().eq(200).all()
assert int(maps.query("recipe=='D1'").common_fp_pixels.sum())==510336
assert int(maps.query("recipe=='D2'").common_fp_pixels.sum())==325593
display(table('combined/pose_x_map_spread.csv').round(4))
show('broad_maps/D1_aggregate_maps.png')
show('broad_maps/D2_aggregate_maps.png')
small=table('small_defects/failure_decomposition.csv')
assert len(small)==58 and small.image_id.nunique()==29
show('small_defects/small_case_decomposition.png')'''),
 md('''## Combined confounders and one future decision

Every missing-label miss is canonical. Six missing-labeled small cases are difficult
for both recipes compared with nonmissing cases in the same coarse size bands;
exact size, source labels and context remain confounded. Reversed anomalies explain
a substantial FP burden but only five images are available. Canonical orientation
normalization is one proposed controlledStage5B test; it has not been executed,
and it is not expected automatically to resolve canonical missing-label misses.'''),
 code('''display(table('combined/pose_x_missing.csv').round(4))
display(table('combined/size_x_missing.csv').round(4))
display(Markdown((base/'combined/decision_summary.md').read_text()))
display(pd.DataFrame(review['saved_map_independent_counts']))
print('Stage4 identity comparisons:',review['stage4_identity_checks'])
print('Query/reference coordinate checks:',review['query_reference_coordinate_checks'])
print('Independent sampled distance checks:',review['subset_distance_checks'])
print('All saved maps reconciled; frozen native trace maps matched exactly.')'''),
 md('''## Verification scope and preserved history

The independent review rechecked all200 diagnostic IDs/flags/scores/pixel AP values,
full common-map FP/intersection/union counts, exact frozen reference indices and
all saved coordinate conversions. Float64 feature distances were checked on190
fixed query subsets; there was no second independent full feature extraction.
Manual center-view contexts include uncertainty; no anatomical causal claim is made.
Earlier preparation-clock and transport caveats remain in the Stage4 history.
The readable journey chapter and final diagnostic receipt link the exact evidence.
No detector parameter or Stage5B model was changed or evaluated.''')]
 nbf.validate(notebook)
 if execute:NotebookClient(notebook,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(root)}}).execute()
 target=root/'notebooks/pcb2_stage5a_diagnostics.ipynb';nbf.write(notebook,target);print(('Executed' if execute else 'Built')+' artifact-only Stage5A notebook')


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--execute',action='store_true');a=p.parse_args();build(a.root,a.execute)
