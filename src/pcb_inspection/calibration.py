"""Normal-only quantile policies; ties remain unflagged."""
import numpy as np


def finite_array(values):
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0 or not np.isfinite(array).all():
        raise ValueError("Nonempty finite values required")
    return array


def calibrate(scores, maps=None):
    scores = finite_array(scores)
    if scores.ndim != 1:
        raise ValueError("Scores must be one-dimensional")
    result = {"image_threshold": float(np.quantile(scores, .95, method="higher")),
              "image_quantile": .95, "pixel_quantile": .99, "quantile_method": "higher",
              "comparison": ">", "normal_calibration_count": len(scores)}
    if maps is not None:
        maps = finite_array(maps)
        if maps.ndim != 3 or len(maps) != len(scores):
            raise ValueError("Maps must be [N,H,W] paired with scores")
        result["pixel_threshold"] = float(np.quantile(maps, .99, method="higher"))
    return result


def flag(scores, threshold):
    if not np.isfinite(threshold):
        raise ValueError("Finite threshold required")
    return finite_array(scores) > threshold
