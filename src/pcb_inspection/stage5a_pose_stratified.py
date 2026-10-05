"""Binary-label-stratified supplement to the immutable pose report."""
from pathlib import Path
import pandas as pd
from .guard import digest,now,write_new

def stratified_summary(frame):
    records=[]
    for recipe in ['d1','d2']:
        for (pose,kind),group in frame.groupby(['pose_label','normal_or_anomaly']):
            fp=group[recipe+'_false_positive_pixels']
            records.append({'recipe':recipe,'pose_label':pose,'normal_or_anomaly':kind,'n_images':len(group),
                'median_fp_pixels':fp.median(),'q25_fp_pixels':fp.quantile(.25),'q75_fp_pixels':fp.quantile(.75),'total_fp_pixels':fp.sum()})
    return pd.DataFrame(records)

def finding_lines(summary):
    lines=['# Binary-label-stratified pose comparison','','Use anomaly-only medians for a like-for-like contrast; canonical contains all100normals as well as90anomalies. The main pose_summary also retains all-image broad-map burden as requested.','']
    for recipe in ['d1','d2']:
        sub=summary[(summary.recipe==recipe)&(summary.normal_or_anomaly=='anomaly')].set_index('pose_label')
        reverse=sub.loc['reversed_180','median_fp_pixels'];canonical=sub.loc['canonical','median_fp_pixels']
        lines.append(f'{recipe.upper()} among anomalies: reversed medianFP {reverse:.0f} vs canonical {canonical:.0f} ({reverse/canonical:.1f}x). Reversed n5, canonical n90; this association is neither a causal estimate nor evidence about reversed normal boards.')
    return '\n'.join(lines)+'\n'

def verify_saved(root):
    out=Path(root)/'artifacts/stage5a/pose';frame=pd.read_csv(out/'pose_diagnostic_table.csv')
    expected=stratified_summary(frame);saved=pd.read_csv(out/'pose_binary_stratified_summary.csv')
    pd.testing.assert_frame_equal(expected,saved,check_dtype=False)
    if (out/'pose_stratified_findings.md').read_text()!=finding_lines(expected):raise ValueError('Stratified findings mismatch')
    write_new(out/'pose_stratified_complete.json',{'verified_at_utc':now(),'post_confirmation':True,
        'input_sha256':digest(out/'pose_diagnostic_table.csv'),'code_sha256':digest(Path(__file__)),
        'outputs':{str(out/name):digest(out/name) for name in ['pose_binary_stratified_summary.csv','pose_stratified_findings.md']}})

if __name__=='__main__':verify_saved('.')
