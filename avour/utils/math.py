import numpy as np
from scipy.interpolate import CubicSpline
from typing import List, Tuple

def clip(val: float, min_val: float, max_val: float) -> float:
    if val < min_val:
        return min_val
    if val > max_val:
        return max_val
    return val

def sign(val: float) -> float:
    return 1 if val >= 0 else -1

def interp_1d(a: float, b: float, factor: float, limit: bool = False) -> float:
    if limit:
        factor = max(min(factor, 1), 0)
    return a + factor * (b - a)

def interp_2d(p0: Tuple[float, float], p1: Tuple[float, float], factor: float) -> Tuple[float, float]:
    return interp_1d(p0[0], p1[0], factor), interp_1d(p0[1], p1[1], factor)

def mapper_1d(cur_src: float, src_a: float, src_b: float, tar_a: float, tar_b: float) -> float:
    factor = (cur_src - src_a) / (src_b - src_a)
    return tar_a + factor * (tar_b - tar_a)

def quadratic_bezier(p0: Tuple[float, float], p1: Tuple[float, float], p2: Tuple[float, float], n_segments: int) -> List[Tuple[float, float]]:
    points = []
    for i in range(n_segments + 1):
        factor = (i / n_segments)
        l0 = interp_2d(p0, p1, factor)
        l1 = interp_2d(p1, p2, factor)
        points.append(interp_2d(l0, l1, factor))
    return points

def cubic_bezier(p0: Tuple[float, float], p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float], n_segments: int) -> List[Tuple[float, float]]:
    points = []
    for i in range(n_segments + 1):
        factor = (i / n_segments)
        l0 = interp_2d(p0, p1, factor)
        l1 = interp_2d(p1, p2, factor)
        l2 = interp_2d(p2, p3, factor)
        q0 = interp_2d(l0, l1, factor)
        q1 = interp_2d(l1, l2, factor)
        points.append(interp_2d(q0, q1, factor))
    return points

def smoothen_1d(points: List[float], factor: float) -> List[float]:
    x = np.linspace(0, len(points) - 1, num=len(points))
    xt = np.linspace(0, len(points) - 1, num=int(len(points) * factor))
    return CubicSpline(x, np.array(points))(xt).tolist()

def smoothen_tuples(points: List[Tuple[float, float]], factor: float) -> List[Tuple[float, float]]:
    return [(x, y) for x, y in zip(smoothen_1d([point[0] for point in points], factor=factor), smoothen_1d([point[1] for point in points], factor=factor))]
