"""Saved-artifact Stage 5B figures. Never fit or run a detector."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

from .geometry import letterbox
from .guard import digest, now, write_new


def build(root):
    root = Path(root).resolve()
    out = root / 'artifacts/stage5b'
    figures = out / 'figures'
    figures.mkdir(exist_ok=False)
    baseline = root / 'artifacts/stage4/pcb2_d1_primary'
    oldpaths = json.loads((baseline / 'array_paths.json').read_text())
    newpaths = json.loads((out / 'array_paths.json').read_text())
    transforms = json.loads((baseline / 'test_transforms.json').read_text())
    pose = pd.read_csv(root / 'artifacts/stage5a/pose/pose_labels.csv')
    ids = sorted(pose.loc[pose.pose_label.eq('reversed_180'), 'image_id'])
    assert len(ids) == 5
    manifest = pd.read_csv(baseline / 'confirmation_manifest.csv', keep_default_na=False).set_index('image_id')
    pixel_t = json.loads((baseline / 'calibration.json').read_text())['pixel_threshold']
    sources = {}
    oldmaps, newmaps = [], []
    source_images, masks, crops, normalized, inputs, natives = [], [], [], [], [], []
    for image_id in ids:
        row = manifest.loc[image_id]
        for path in [row.image_path, row.mask_path]:
            sources[path] = digest(root / path)
        image = Image.open(root / row.image_path).convert('RGB')
        mask = np.asarray(Image.open(root / row.mask_path).resize((256, 256), Image.Resampling.NEAREST)) > 0
        source_images.append(image.resize((256, 256)))
        masks.append(mask)
        t = transforms[image_id]
        crop = image.crop(t['crop_box'])
        flipped = Image.fromarray(np.asarray(crop)[::-1, ::-1].copy())
        rotated_source = image.copy(); rotated_source.paste(flipped, tuple(t['crop_box'][:2]))
        canvas, _ = letterbox(rotated_source, t, 256)
        crops.append(crop); normalized.append(flipped); inputs.append(canvas)
        oldmaps.append(np.load(root / oldpaths['anomaly_maps'] / f'{image_id}.npy'))
        newmaps.append(np.load(root / newpaths['anomaly_maps'] / f'{image_id}.npy'))
        natives.append(np.load(root / newpaths['model_maps'] / f'{image_id}.npy'))
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    fig, axes = plt.subplots(5, 5, figsize=(16, 16), constrained_layout=True)
    for i, image_id in enumerate(ids):
        axes[i, 0].imshow(source_images[i]); axes[i, 0].set_ylabel(image_id[:12])
        axes[i, 1].imshow(masks[i], cmap='gray', vmin=0, vmax=1)
        for j, array in [(2, oldmaps[i]), (3, newmaps[i])]:
            artist = axes[i, j].imshow(array / pixel_t, cmap='magma', vmin=0, vmax=3)
            axes[i, j].contour(masks[i], levels=[.5], colors=['#72c9d1'], linewidths=.65)
        difference = axes[i, 4].imshow((newmaps[i]-oldmaps[i])/pixel_t, cmap='coolwarm', vmin=-3, vmax=3)
        for ax in axes[i]: ax.set_xticks([]); ax.set_yticks([])
    for ax, title in zip(axes[0], ['Original image', 'Union GT mask', 'Historical D1', 'Orientation D1', 'New − historical']): ax.set_title(title)
    fig.colorbar(artist, ax=axes[:, 2:4], shrink=.55, label='Score / frozen pixel threshold; not probability')
    fig.colorbar(difference, ax=axes[:, 4], shrink=.55, label='Score change / frozen threshold')
    fig.suptitle('All five reversed PCB2 anomalies · maps returned to original source coordinates')
    fig.savefig(figures / 'reversed_before_after.png', dpi=150); plt.close(fig)
    fig, axes = plt.subplots(5, 5, figsize=(16, 16), constrained_layout=True)
    for i, image_id in enumerate(ids):
        for j, im in enumerate([crops[i], normalized[i], inputs[i]]): axes[i, j].imshow(im)
        a = axes[i, 3].imshow(natives[i]/pixel_t, cmap='magma', vmin=0, vmax=3)
        axes[i, 4].imshow(newmaps[i]/pixel_t, cmap='magma', vmin=0, vmax=3)
        axes[i, 0].set_ylabel(image_id[:12])
        for ax in axes[i]: ax.set_xticks([]); ax.set_yticks([])
    for ax, title in zip(axes[0], ['Historical crop', 'Exact 180° crop', 'D1 letterbox', 'Normalized native map', 'Inverse-rotated common map']): ax.set_title(title)
    fig.colorbar(a, ax=axes[:, 3:], shrink=.55, label='Score / frozen pixel threshold; not probability')
    fig.suptitle('Orientation geometry · crop rotation precedes resize · inverse rotation precedes source paste')
    fig.savefig(figures / 'orientation_geometry.png', dpi=150); plt.close(fig)
    fig, axes = plt.subplots(5, 3, figsize=(11, 15), constrained_layout=True)
    for i, image_id in enumerate(ids):
        old, new, gt = oldmaps[i], newmaps[i], masks[i]
        removed = (old>pixel_t)&(new<=pixel_t)
        added = (new>pixel_t)&(old<=pixel_t)
        a=axes[i, 0].imshow((new-old)/pixel_t, cmap='coolwarm', vmin=-3, vmax=3)
        axes[i, 1].imshow(removed, cmap='gray', vmin=0, vmax=1)
        axes[i, 2].imshow(added, cmap='gray', vmin=0, vmax=1)
        for ax in axes[i]:
            ax.contour(gt, levels=[.5], colors=['#72c9d1'], linewidths=.7)
            ax.set_xticks([]); ax.set_yticks([])
        axes[i, 0].set_ylabel(image_id[:12])
        axes[i, 1].set_xlabel(f'Removed outside GT: {int((removed&~gt).sum()):,}; inside: {int((removed&gt).sum()):,}')
        axes[i, 2].set_xlabel(f'Added outside GT: {int((added&~gt).sum()):,}; inside: {int((added&gt).sum()):,}')
    for ax,title in zip(axes[0], ['Score change / threshold', 'Disappeared exceedances', 'New exceedances']): ax.set_title(title)
    fig.colorbar(a, ax=axes[:, 0], shrink=.55)
    fig.suptitle('Common 256×256 difference diagnostics · cyan contour = original union GT')
    fig.savefig(figures / 'reversed_map_differences.png', dpi=150); plt.close(fig)
    oldpred = pd.read_csv(baseline / 'predictions.csv').set_index('image_id')
    newpred = pd.read_csv(out / 'predictions.csv').set_index('image_id')
    for name, ylabel, historical, modified in [
        ('reversed_fp_pixels', 'False-positive pixels (common 256×256)', [int(((x>pixel_t)&~g).sum()) for x,g in zip(oldmaps,masks)], [int(((x>pixel_t)&~g).sum()) for x,g in zip(newmaps,masks)]),
        ('reversed_pixel_ap', 'Per-image pixel average precision', oldpred.loc[ids,'pixel_ap'], newpred.loc[ids,'pixel_ap'])]:
        fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
        positions=np.arange(5)
        ax.bar(positions-.18, historical, .36, color='#566b82', label='Historical Stage 4 D1')
        ax.bar(positions+.18, modified, .36, color='#b97530', label='Stage 5B orientation D1')
        ax.set_xticks(positions, [x[:12] for x in ids]); ax.set_ylabel(ylabel); ax.set_ylim(bottom=0)
        ax.set_title('All five reversed anomalies'); ax.legend()
        fig.savefig(figures / f'{name}.png', dpi=160); plt.close(fig)
    runtime = pd.read_csv(out/'results/runtime.csv')
    timer_columns = [c for c in ['pose_seconds','rotation_seconds','total_preprocessing_seconds',
                                'd1_inference_seconds','inverse_map_seconds','end_to_end_seconds'] if c in runtime]
    fig,ax = plt.subplots(figsize=(11,5),constrained_layout=True)
    positions=np.arange(len(timer_columns))
    ax.bar(positions-.18,[runtime[c].median()*1000 for c in timer_columns],.36,color='#566b82',label='Median')
    ax.bar(positions+.18,[runtime[c].quantile(.95)*1000 for c in timer_columns],.36,color='#b97530',label='p95')
    ax.set_xticks(positions,[c.replace('_seconds','').replace('_','\n') for c in timer_columns])
    ax.set_ylabel('Milliseconds per image');ax.set_ylim(bottom=0);ax.legend()
    ax.set_title('Stage 5B timing components · nested measurements, do not sum bars')
    fig.savefig(figures/'runtime.png',dpi=160);plt.close(fig)
    names = [str((baseline / 'array_paths.json').relative_to(root)), str((out / 'array_paths.json').relative_to(root)),
             str((baseline / 'test_transforms.json').relative_to(root)), str((baseline / 'calibration.json').relative_to(root)),
             str((baseline / 'predictions.csv').relative_to(root)), str((out / 'predictions.csv').relative_to(root)),
             'artifacts/stage5a/pose/pose_labels.csv', 'src/pcb_inspection/stage5b_report.py',
             'artifacts/stage5b/results/runtime.csv']
    for name in names: sources[name] = digest(root/name)
    for paths in [oldpaths,newpaths]:
        for image_id in ids:
            for key in ['model_maps','anomaly_maps']:
                name = str(Path(paths[key])/f'{image_id}.npy'); sources[name] = digest(root/name)
    write_new(out/'figure_metadata.json', {'created_at_utc':now(), 'new_inference':False,
        'ids':ids, 'scale':'map / frozen pixel threshold; magma 0..3; signed changes -3..3',
        'sources':sources, 'outputs':{str(p.relative_to(root)):digest(p) for p in sorted(figures.glob('*.png'))}})


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--root',default='.'); args=p.parse_args(); build(args.root)
