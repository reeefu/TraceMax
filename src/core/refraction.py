import numpy as np


def linear_regression(x, y):
    """Ordinary least-squares linear fit: y = slope * x + intercept.

    Returns:
        (slope, intercept, r_squared)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    if n < 2:
        return 0.0, 0.0, 0.0

    sx = x.sum()
    sy = y.sum()
    sxx = (x * x).sum()
    sxy = (x * y).sum()

    denom = n * sxx - sx * sx
    if abs(denom) < 1e-15:
        return 0.0, 0.0, 0.0

    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n

    y_pred = slope * x + intercept
    ss_res = ((y - y_pred) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-15 else 0.0

    return slope, intercept, r_squared


# ---------------------------------------------------------------------------
# Crossover detection methods
# ---------------------------------------------------------------------------

def find_crossover(offsets, times, method='kneepoint'):
    """Auto-detect crossover point between direct and refracted arrivals.

    Args:
        offsets: 1D array of distances.
        times: 1D array of arrival times.
        method: 'kneepoint' for incremental regression residual method,
                'mse' for two-segment minimum total residual method.

    Returns the index of the crossover point, or None if not found.
    """
    if method == 'kneepoint':
        idx, _ = find_crossover_kneepoint(offsets, times)
        return idx
    else:
        return find_crossover_mse(offsets, times)


def find_crossover_mse(offsets, times):
    """Auto-detect crossover using two-segment MSE minimization.

    Returns the index of the crossover point, or None if not found.
    """
    offsets = np.asarray(offsets, dtype=float)
    times = np.asarray(times, dtype=float)
    n = len(offsets)
    if n < 4:
        return None

    if np.ptp(offsets) < 1e-10:
        return None

    best_err = np.inf
    best_idx = None

    for i in range(2, n - 1):
        s1, i1, _ = linear_regression(offsets[:i + 1], times[:i + 1])
        s2, i2, _ = linear_regression(offsets[i:], times[i:])

        pred1 = s1 * offsets[:i + 1] + i1
        pred2 = s2 * offsets[i:] + i2
        err = ((times[:i + 1] - pred1) ** 2).sum() + ((times[i:] - pred2) ** 2).sum()

        if err < best_err:
            best_err = err
            best_idx = i

    return best_idx


def find_crossover_kneepoint(offsets, times):
    """Detect crossover using the knee-point method (incremental regression).

    Algorithm:
      1. For each index t from 3 to N, fit a line to points [0..t]
         and collect the sum of squared residuals.
      2. Detrend the residual curve by subtracting a straight line
         from first to last residual value.
      3. The minimum of the detrended curve is the knee point — where
         the data transitions from direct wave to refracted wave.

    Args:
        offsets: 1D array of distances.
        times: 1D array of arrival times.

    Returns:
        (knee_index, residuals_detrended) — the index into the original
        arrays where crossover occurs, and the detrended residual curve
        for plotting. Returns (None, []) if insufficient data.
    """
    offsets = np.asarray(offsets, dtype=float)
    times = np.asarray(times, dtype=float)
    n = len(offsets)

    if n < 4:
        return None, []

    if np.ptp(offsets) < 1e-10:
        return None, []

    # Collect sum-of-squared-residuals for incremental fits
    residuals = []
    for t in range(3, n + 1):
        coeffs = np.polyfit(offsets[:t], times[:t], 1, full=True)
        if len(coeffs[1]) > 0:
            residuals.append(coeffs[1][0])
        else:
            # polyfit may return empty residuals for exact fits
            pred = np.polyval(coeffs[0], offsets[:t])
            residuals.append(((times[:t] - pred) ** 2).sum())

    if len(residuals) < 2:
        return None, []

    residuals = np.array(residuals, dtype=float)

    # Detrend: subtract a straight line from first to last value
    xx = np.linspace(0, 1, len(residuals))
    line = np.polyfit([0, 1], [residuals[0], residuals[-1]], 1)
    trend = line[0] * xx + line[1]
    detrended = residuals - trend

    # Knee point = minimum of the detrended residual curve
    knee_local = int(np.argmin(detrended))

    # Map back to original array index (offset of 3 from the loop start,
    # then +1 because the index represents the boundary)
    # t=3 means we fit points [0..2], so crossover would be at index 2
    # knee_local=0 corresponds to t=3, which means index 2+1 = 3
    knee_index = knee_local + 3  # index into original arrays

    # Clamp to valid range
    knee_index = min(knee_index, n - 1)
    knee_index = max(1, knee_index)

    return knee_index, detrended.tolist()


# ---------------------------------------------------------------------------
# Single-direction analysis
# ---------------------------------------------------------------------------

def slope_intercept_analysis(offsets, times, crossover_idx=None, method='kneepoint'):
    """Fit two linear segments (direct + refracted) to travel-time data.

    Args:
        offsets: 1D array of source-receiver distances (m).
        times: 1D array of arrival times (s).
        crossover_idx: index separating direct from refracted.
                       If None, auto-detected.
        method: 'kneepoint' or 'mse' for auto-detection method.

    Returns dict with:
        'direct':    (slope, intercept, r2)
        'refracted': (slope, intercept, r2)  or None if only direct
        'crossover_idx': int
        'crossover_distance': float
        'v_direct': float (m/s) — velocity of direct wave
        'v_refracted': float (m/s) — velocity of refracted wave (or None)
        'kneepoint_residuals': list — detrended residuals (empty if MSE used)
    """
    offsets = np.asarray(offsets, dtype=float)
    times = np.asarray(times, dtype=float)

    kneepoint_residuals = []

    if crossover_idx is None:
        if method == 'kneepoint':
            crossover_idx, kneepoint_residuals = find_crossover_kneepoint(offsets, times)
        else:
            crossover_idx = find_crossover_mse(offsets, times)

    result = {}

    if crossover_idx is None or crossover_idx >= len(offsets) - 1:
        # Only direct wave
        s, i, r2 = linear_regression(offsets, times)
        v = 1.0 / s if abs(s) > 1e-15 else 0.0
        result['direct'] = (s, i, r2)
        result['refracted'] = None
        result['crossover_idx'] = len(offsets) - 1
        result['crossover_distance'] = offsets[-1]
        result['v_direct'] = abs(v)
        result['v_refracted'] = None
        result['kneepoint_residuals'] = kneepoint_residuals
        return result

    s1, i1, r2_1 = linear_regression(offsets[:crossover_idx + 1], times[:crossover_idx + 1])
    s2, i2, r2_2 = linear_regression(offsets[crossover_idx:], times[crossover_idx:])

    v1 = 1.0 / s1 if abs(s1) > 1e-15 else 0.0
    v2 = 1.0 / s2 if abs(s2) > 1e-15 else 0.0

    result['direct'] = (s1, i1, r2_1)
    result['refracted'] = (s2, i2, r2_2)
    result['crossover_idx'] = crossover_idx
    result['crossover_distance'] = offsets[crossover_idx]
    result['v_direct'] = abs(v1)
    result['v_refracted'] = abs(v2)
    result['kneepoint_residuals'] = kneepoint_residuals

    return result


def hagiwara_analysis(offsets, times, crossover_idx=None, method='kneepoint'):
    """Hagiwara (1939) method for seismic refraction interpretation.

    Computes:
      - Layer 1 velocity (V1) from direct wave slope
      - Layer 2 velocity (V2) from refracted wave slope
      - Layer 1 thickness (h1) from the intercept time:
            ti = 2 * h1 * sqrt(1/V1^2 - 1/V2^2)
            h1 = ti / (2 * sqrt(1/V1^2 - 1/V2^2))
      - Crossover distance (Xc)
      - Critical angle: ic = arcsin(V1/V2)
      - Depth to interface at any offset using the delay-time method

    Args:
        offsets: 1D array of source-receiver distances (m).
        times: 1D array of arrival times (s).
        crossover_idx: manual crossover index (auto-detected if None).
        method: 'kneepoint' or 'mse' for crossover detection.

    Returns dict with:
        'v1': float — Layer 1 velocity (m/s)
        'v2': float — Layer 2 velocity (m/s)
        'h1': float — Layer 1 thickness (m)
        'crossover_distance': float (m)
        'intercept_time': float (s)
        'critical_angle_deg': float (degrees)
        'slope_intercept': dict from slope_intercept_analysis
        'depth_profile': list of (offset, depth) — depth to interface
    """
    offsets = np.asarray(offsets, dtype=float)
    times = np.asarray(times, dtype=float)

    si = slope_intercept_analysis(offsets, times, crossover_idx, method=method)

    v1 = si['v_direct']
    v2 = si.get('v_refracted')

    result = {
        'v1': v1,
        'v2': v2,
        'h1': None,
        'crossover_distance': si['crossover_distance'],
        'intercept_time': None,
        'critical_angle_deg': None,
        'slope_intercept': si,
        'depth_profile': [],
    }

    if v2 is None or v1 <= 0 or v2 <= 0 or v2 <= v1:
        return result

    # Intercept time from refracted line
    ti = si['refracted'][1]  # intercept of the refracted line
    result['intercept_time'] = ti

    # Critical angle
    sin_ic = v1 / v2
    if sin_ic >= 1.0:
        return result
    ic = np.arcsin(sin_ic)
    result['critical_angle_deg'] = np.degrees(ic)

    # Layer 1 thickness from intercept time
    # ti = 2 * h1 * cos(ic) / V1
    cos_ic = np.cos(ic)
    if cos_ic > 1e-15:
        h1 = (ti * v1) / (2.0 * cos_ic)
        result['h1'] = abs(h1)

    # Depth profile using delay-time method
    depth_profile = []
    factor = (v1 * v2) / (2.0 * np.sqrt(v2**2 - v1**2))

    cidx = si['crossover_idx']
    for i in range(cidx, len(offsets)):
        dt = times[i] - offsets[i] / v2
        depth = abs(dt * factor)
        depth_profile.append((float(offsets[i]), depth))

    result['depth_profile'] = depth_profile

    return result


# ---------------------------------------------------------------------------
# Two-direction (TAP/TBP) Hagiwara analysis
# ---------------------------------------------------------------------------

def hagiwara_two_direction(tap_times, tbp_times, positions, spacing=None,
                           method='kneepoint', cross_idx_forward=None,
                           cross_idx_backward=None):
    """Full Hagiwara analysis using forward (TAP) and backward (TBP) shots.

    This implements the full two-direction Hagiwara method as in the
    standalone plugin. Both shot directions are analysed to produce
    forward and backward velocities, refraction coefficients, and a
    subsurface depth profile.

    Args:
        tap_times: 1D array of forward-shot arrival times (s).
                   Should include zero-offset (0.0) as first element,
                   or it will be prepended automatically.
        tbp_times: 1D array of backward-shot arrival times (s).
                   Same convention as tap_times.
        positions: 1D array of geophone positions (m), or None.
                   If None, positions are computed from spacing.
        spacing: float — uniform geophone spacing (m). Used only if
                 positions is None. Default 2.0.
        method: 'kneepoint' or 'mse' for crossover auto-detection.
        cross_idx_forward: int or None — manual crossover index for
                           forward shot. Overrides auto-detection.
        cross_idx_backward: int or None — manual crossover index for
                            backward shot. Overrides auto-detection.

    Returns dict with:
        'positions': list of geophone positions
        'tap': list of forward arrival times (with zero offset)
        'tbp': list of backward arrival times (with zero offset)
        'knee_forward': int — knee index for forward shot
        'knee_backward': int — knee index for backward shot
        'knee_residuals_forward': list — detrended residuals for forward
        'knee_residuals_backward': list — detrended residuals for backward
        'forward_coeff': (slope, intercept) — direct wave fit forward
        'backward_coeff': (slope, intercept) — direct wave fit backward
        'refraction_forward_coeff': (slope, intercept) — refracted fit forward
        'refraction_backward_coeff': (slope, intercept) — refracted fit backward
        'offset_forward': float — x-intercept of forward direct line
        'offset_backward': float — x-intercept of backward direct line
        'v1': float — layer 1 velocity (average of forward/backward)
        'v2': float — layer 2 velocity (harmonic mean of refraction velocities)
        'cosine': float — cos(critical angle)
        'distance': list — adjusted distance profile
        'depth': list — depth to interface at each position
        'tab': float — total travel time from A to B
        'refraction_tap': list — Hagiwara delay times (forward)
        'refraction_tbp': list — Hagiwara delay times (backward)
    """
    if spacing is None:
        spacing = 2.0

    tap = np.asarray(tap_times, dtype=float)
    tbp = np.asarray(tbp_times, dtype=float)

    # Ensure zero-offset is present (prepend 0.0 if first value != 0)
    if len(tap) > 0 and tap[0] != 0.0:
        tap = np.insert(tap, 0, 0.0)
    if len(tbp) > 0 and tbp[0] != 0.0:
        tbp = np.insert(tbp, 0, 0.0)

    # Ensure tap and tbp have the same length after zero-offset insertion
    if len(tap) != len(tbp):
        max_len = max(len(tap), len(tbp))
        if len(tap) < max_len:
            tap = np.pad(tap, (0, max_len - len(tap)), constant_values=tap[-1])
        if len(tbp) < max_len:
            tbp = np.pad(tbp, (0, max_len - len(tbp)), constant_values=tbp[-1])

    nd = len(tap)

    # Build positions array
    if positions is not None:
        pos = np.asarray(positions, dtype=float)
        # Ensure correct length (may need to match tap length)
        if len(pos) < nd:
            pos = np.arange(0, nd) * spacing
    else:
        pos = np.arange(0, nd) * spacing

    # Total travel time A to B
    tab = (tap[-1] + tbp[-1]) / 2.0

    # --- Knee-point / crossover detection ---
    x = pos[1:]
    a = tap[1:]
    b = tbp[1:]

    if cross_idx_forward is not None and cross_idx_forward > 0:
        # Manual forward crossover
        kac = cross_idx_forward
        res_fwd = []
    elif method == 'mse':
        kac = _crossover_single_mse(x, a)
        res_fwd = []
    else:
        kac, res_fwd = _kneepos_single(x, a)

    if cross_idx_backward is not None and cross_idx_backward > 0:
        # Manual backward crossover
        kbc = cross_idx_backward
        res_bwd = []
    elif method == 'mse':
        kbc = _crossover_single_mse(x, b)
        res_bwd = []
    else:
        kbc, res_bwd = _kneepos_single(x, b)

    # ka, kb: indices for the analysis (1-based from zero-offset insertion)
    ka = kac + 1
    kb = kbc + 1

    # --- Direct wave linear fits ---
    koefa = np.polyfit(x[:kac], a[:kac], 1)  # forward direct
    koefb = np.polyfit(x[:kbc], b[:kbc], 1)  # backward direct

    # X-intercepts of direct wave lines
    offa = -koefa[1] / koefa[0] if abs(koefa[0]) > 1e-15 else 0.0
    offb = -koefb[1] / koefb[0] if abs(koefb[0]) > 1e-15 else 0.0

    # Direct wave fit lines
    t_ap = koefa[0] * pos + koefa[1]
    t_bp = koefb[0] * pos + koefb[1]

    # Flip TBP for plotting (backward shot)
    tbp_flipped = np.flip(tbp)
    t_bp_flipped = np.flip(t_bp)

    # --- Hagiwara delay-time computation ---
    hap = []
    hbp = []

    for i in range(ka, nd - kb):
        ta_i = tap[i]
        tb_i = tbp_flipped[i]
        hh = (ta_i + tb_i - tab) / 2.0
        ha = ta_i - hh
        hb = tb_i - hh
        hap.append(ha)
        hbp.append(hb)

    hx = pos[ka:nd - kb]

    # Refraction line fits — handle edge cases with few refraction points
    if len(hx) >= 2 and len(hap) >= 2:
        koefha = np.polyfit(hx, hap, 1)
        koefhb = np.polyfit(hx, hbp, 1)
    elif len(hap) == 1:
        # Single refraction point: use a flat line through that point
        koefha = np.array([0.0, hap[0]])
        koefhb = np.array([0.0, hbp[0]])
    else:
        # No refraction points: estimate from direct wave slopes
        # Use the remaining (post-knee) data to fit a second segment
        if ka < nd and nd - kb > ka:
            seg_a = tap[ka:]
            seg_b = tbp_flipped[ka:] if ka < len(tbp_flipped) else tbp_flipped
            pos_seg = pos[ka:len(seg_a) + ka]
            if len(pos_seg) >= 2:
                koefha = np.polyfit(pos_seg, seg_a, 1)
                koefhb = np.polyfit(pos_seg[:len(seg_b)], seg_b[:len(pos_seg)], 1)
            else:
                koefha = np.array([koefa[0], koefa[1]])
                koefhb = np.array([koefb[0], koefb[1]])
        else:
            koefha = np.array([koefa[0], koefa[1]])
            koefhb = np.array([koefb[0], koefb[1]])

    th_ap = koefha[0] * pos + koefha[1]  # T'ap
    th_bp = koefhb[0] * pos + koefhb[1]  # T'bp

    tA = koefha[0] * offa + koefha[1]
    tB = koefhb[0] * (pos[-1] - offb) + koefhb[1]

    # --- Velocities ---
    v1 = (abs(1.0 / koefa[0]) + abs(1.0 / koefb[0])) / 2.0
    va = 1.0 / koefha[0] if abs(koefha[0]) > 1e-15 else 1e6
    vb = 1.0 / koefhb[0] if abs(koefhb[0]) > 1e-15 else 1e6
    v2 = 2.0 * (va * abs(vb)) / (va + abs(vb)) if (va + abs(vb)) > 0 else 0.0

    # Critical angle
    if v2 > v1 and v1 > 0:
        cosi = np.sqrt(v2 * v2 - v1 * v1) / v2
    else:
        cosi = 0.0

    # --- Depth profile ---
    hh = []
    xx = []

    if cosi > 1e-15:
        hh.append(v1 * tA / cosi)
    else:
        hh.append(0.0)
    xx.append(0.0)

    for i in range(ka):
        hp = (tbp_flipped[i] - th_bp[i]) * v1 / cosi if cosi > 1e-15 else 0.0
        hh.append(hp)
        xx.append(pos[i] - offa)

    for i in range(ka + 1, nd - kb):
        hp = (tap[i] + tbp_flipped[i] - tab) * v1 / (2.0 * cosi) if cosi > 1e-15 else 0.0
        hh.append(hp)
        xx.append(pos[i] - offa)

    for i in range(nd - kb + 1, nd):
        hp = (tap[i] - th_ap[i]) * v1 / cosi if cosi > 1e-15 else 0.0
        hh.append(hp)
        xx.append(pos[i] - offa)

    if cosi > 1e-15:
        hh.append(v1 * tB / cosi)
    else:
        hh.append(0.0)
    xx.append(pos[-1] - offa - offb)

    return {
        'positions': pos.tolist(),
        'tap': tap.tolist(),
        'tbp': tbp.tolist(),
        'knee_forward': kac,
        'knee_backward': kbc,
        'knee_residuals_forward': res_fwd,
        'knee_residuals_backward': res_bwd,
        'forward_coeff': koefa.tolist(),
        'backward_coeff': koefb.tolist(),
        'refraction_forward_coeff': koefha.tolist(),
        'refraction_backward_coeff': koefhb.tolist(),
        'offset_forward': float(offa),
        'offset_backward': float(offb),
        'v1': float(v1),
        'v2': float(v2),
        'cosine': float(cosi),
        'distance': [float(x) for x in xx],
        'depth': [float(h) for h in hh],
        'tab': float(tab),
        'refraction_tap': [float(h) for h in hap],
        'refraction_tbp': [float(h) for h in hbp],
    }


def _kneepos_single(x, times):
    """Compute knee-point for a single direction.

    Args:
        x: 1D array of positions (excluding zero offset).
        times: 1D array of arrival times (excluding zero offset).

    Returns:
        (knee_index, detrended_residuals)
        knee_index is 1-based from the start of x (suitable for slicing).
    """
    x = np.asarray(x, dtype=float)
    times = np.asarray(times, dtype=float)
    n = len(x)

    if n < 4:
        return n // 2, []

    residuals = []
    for t in range(3, n + 1):
        fit = np.polyfit(x[:t], times[:t], 1, full=True)
        if len(fit[1]) > 0:
            residuals.append(fit[1][0])
        else:
            pred = np.polyval(fit[0], x[:t])
            residuals.append(((times[:t] - pred) ** 2).sum())

    if len(residuals) < 2:
        return n // 2, []

    residuals = np.array(residuals, dtype=float)

    # Detrend
    xx = np.linspace(0, 1, len(residuals))
    line = np.polyfit([0, 1], [residuals[0], residuals[-1]], 1)
    trend = line[0] * xx + line[1]
    detrended = residuals - trend

    # Knee = minimum of detrended curve
    knee_local = int(np.argmin(detrended))

    # Map back: knee_local=0 → t=3 → index 3 in the x array (1-based)
    knee_index = knee_local + 3
    knee_index = min(knee_index, n)
    knee_index = max(1, knee_index)

    return knee_index, detrended.tolist()


def _crossover_single_mse(x, times):
    """Detect crossover for a single direction using two-segment MSE minimization.

    Args:
        x: 1D array of positions (excluding zero offset).
        times: 1D array of arrival times (excluding zero offset).

    Returns:
        knee_index: int — crossover index (1-based from the start of x).
    """
    x = np.asarray(x, dtype=float)
    times = np.asarray(times, dtype=float)
    n = len(x)

    if n < 4:
        return n // 2

    best_err = np.inf
    best_idx = None

    for i in range(2, n - 1):
        s1, i1, _ = linear_regression(x[:i + 1], times[:i + 1])
        s2, i2, _ = linear_regression(x[i:], times[i:])

        pred1 = s1 * x[:i + 1] + i1
        pred2 = s2 * x[i:] + i2
        err = ((times[:i + 1] - pred1) ** 2).sum() + ((times[i:] - pred2) ** 2).sum()

        if err < best_err:
            best_err = err
            best_idx = i

    if best_idx is None:
        return n // 2

    # Return 1-based index consistent with _kneepos_single
    return max(1, best_idx)
