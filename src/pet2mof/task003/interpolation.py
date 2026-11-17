"""Piecewise-linear interpolation and deterministic coordinate-corner envelopes."""
from itertools import product
import math


def interpolate(p_bar, q_mmol_g, target_p_bar):
    if len(p_bar) != len(q_mmol_g) or len(p_bar) < 2:
        raise ValueError("two or more paired coordinates required")
    if not all(math.isfinite(v) for v in (*p_bar, *q_mmol_g, target_p_bar)):
        raise ValueError("finite coordinates required")
    if any(b <= a for a, b in zip(p_bar, p_bar[1:])):
        raise ValueError("pressures must increase")
    if not p_bar[0] <= target_p_bar <= p_bar[-1]:
        raise ValueError("extrapolation forbidden")
    for i in range(1, len(p_bar)):
        if target_p_bar <= p_bar[i]:
            t = (target_p_bar - p_bar[i-1]) / (p_bar[i] - p_bar[i-1])
            return (1-t) * q_mmol_g[i-1] + t * q_mmol_g[i]
    raise AssertionError("unreachable")


def coordinate_corner_envelope(p_bar, q_mmol_g, target_p_bar, p_half_bar=.042, q_half_mmol_g=.105):
    """All pressure vertices, exact extrema over independent q vertices.

    Interpolation weights are nonnegative, so all lower/all upper q attain
    the q extrema at each pressure vertex. Unsupported vertices are counted,
    not extrapolated. Their full envelope remains unknown.
    """
    if p_half_bar < 0 or q_half_mmol_g < 0:
        raise ValueError("negative coordinate halfwidth")
    values, unsupported, outside_support, unordered = [], 0, 0, 0
    for signs in product((-1, 1), repeat=len(p_bar)):
        p = [v + sign * p_half_bar for v, sign in zip(p_bar, signs)]
        if any(y <= x for x,y in zip(p,p[1:])):
            unordered += 1
            unsupported += 1
            continue
        if not p[0] <= target_p_bar <= p[-1]:
            outside_support += 1
            unsupported += 1
            continue
        try:
            q = interpolate(p, q_mmol_g, target_p_bar)
        except ValueError:
            unsupported += 1
            continue
        values.extend((q - q_half_mmol_g, q + q_half_mmol_g))
    # Intersect the coordinate box with interpolation support. Its new
    # vertices include p_i=target, especially the last UiO-66 point. Merely
    # dropping unsupported box corners would miss this attainable extremum.
    choices = [tuple(sorted(set((p-p_half_bar, p+p_half_bar)
                   + ((target_p_bar,) if p-p_half_bar <= target_p_bar <= p+p_half_bar else ()))))
               for p in p_bar]
    boundary_vertices = 0
    for p in product(*choices):
        if target_p_bar not in p:
            continue
        try:
            q = interpolate(p, q_mmol_g, target_p_bar)
        except ValueError:
            continue
        boundary_vertices += 1
        values.extend((q-q_half_mmol_g, q+q_half_mmol_g))
    return dict(q_low_supported_mmol_g=min(values) if values else None,
                q_high_supported_mmol_g=max(values) if values else None,
                pressure_vertices=2**len(p_bar), unsupported_vertices=unsupported,
                outside_support_vertices=outside_support, unordered_vertices=unordered,
                support_boundary_vertices=boundary_vertices,
                full_envelope_known=outside_support == 0 and bool(values))
