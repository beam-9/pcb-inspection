"""Final retrospective metrics with explicit denominator and undefined cases."""
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from .calibration import finite_array, flag


def binary_labels(values):
    array = np.asarray(values)
    if array.size == 0 or not np.isin(array, [0, 1]).all():
        raise ValueError("Nonempty binary labels required")
    return array.astype(bool)


def safe_divide(numerator, denominator):
    return float(numerator/denominator) if denominator else None


def image_metrics(labels, scores, threshold):
    labels, scores = binary_labels(labels), finite_array(scores)
    if labels.ndim != 1 or labels.shape != scores.shape:
        raise ValueError("Paired one-dimensional labels/scores required")
    predicted = flag(scores, threshold)
    tp = int(np.sum(labels & predicted)); fp = int(np.sum(~labels & predicted))
    fn = int(np.sum(labels & ~predicted)); tn = int(np.sum(~labels & ~predicted))
    positives, negatives = int(labels.sum()), int((~labels).sum())
    return {"n_images": len(labels), "anomaly_count": positives, "normal_count": negatives,
            "anomaly_prevalence": positives/len(labels), "threshold": float(threshold),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": safe_divide(tp, tp+fp), "recall": safe_divide(tp, positives),
            "normal_false_alarm_rate": safe_divide(fp, negatives),
            "average_precision": float(average_precision_score(labels, scores)) if positives else None,
            "auroc": float(roc_auc_score(labels, scores)) if positives and negatives else None}


def localization_metrics(masks, maps, pixel_threshold):
    masks, maps = binary_labels(masks), finite_array(maps)
    if masks.ndim != 3 or masks.shape != maps.shape:
        raise ValueError("Masks/maps must share [N,H,W] geometry")
    predicted = flag(maps, pixel_threshold)
    intersection = int(np.sum(masks & predicted)); union = int(np.sum(masks | predicted))
    positives = int(masks.sum())
    return {"pixel_average_precision": float(average_precision_score(masks.ravel(), maps.ravel())) if positives else None,
            "n_images": len(masks), "n_pixels": masks.size, "positive_pixels": positives,
            "includes_normal_images": True, "pixel_threshold": float(pixel_threshold),
            "intersection_pixels": intersection, "union_pixels": union,
            "pixel_iou": safe_divide(intersection, union)}
