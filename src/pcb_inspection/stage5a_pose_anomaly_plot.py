"""Anomaly-only FP supplement; preserves the existing all-image figure."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .guard import digest,now,write_new

def create(root):
    out=Path(root)/'artifacts/stage5a/pose';target=out/'pose_fp_pixels_anomalies.png'
    if target.exists():raise FileExistsError('Refuse plot overwrite')
    table=out/'pose_diagnostic_table.csv';frame=pd.read_csv(table);anomaly=frame[frame.normal_or_anomaly=='anomaly']
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,recipe in zip(axes,['d1','d2']):
        for index,pose in enumerate(['canonical','reversed_180','uncertain']):
            values=anomaly[anomaly.pose_label==pose][recipe+'_false_positive_pixels'].to_numpy()
            ax.scatter(index+np.linspace(-.13,.13,len(values)),values,s=18,alpha=.5)
            ax.plot([index-.2,index+.2],[np.median(values)]*2,color='black',linewidth=2)
        ax.set_xticks(range(3),['Canonical n=90','Reversed n=5','Uncertain cue n=5']);ax.set_title(recipe.upper());ax.set_yscale('symlog',linthresh=100);ax.grid(axis='y',alpha=.25)
    axes[0].set_ylabel('False-positive common256 pixels (anomalies only)');fig.suptitle('Post-confirmation diagnosis: like-for-like binary-label comparison');fig.tight_layout();fig.savefig(target,dpi=160);plt.close(fig)
    notes=out/'pose_findings_addendum.md'
    notes.write_text('# Pose findings: anomaly-only comparison\n\nUse [the anomaly-only FP figure](pose_fp_pixels_anomalies.png) and `pose_binary_stratified_summary.csv` for the primary like-for-like comparison. D1 reversed medianFP29180 vs canonical2639.5 (11.1x); D2 reversed19367 vs canonical1577.5 (12.3x). All-image medians in `pose_findings.md` mix100canonical normals with90canonical anomalies and should not be treated as the anomaly-only contrast. The five uncertain cases have damaged connector cues and are not verified reversed poses.\n')
    write_new(out/'pose_anomaly_plot_complete.json',{'completed_at_utc':now(),'input_sha256':digest(table),'code_sha256':digest(Path(__file__)),
        'outputs':{str(p):digest(p) for p in [target,notes]}})

if __name__=='__main__':create('.')
