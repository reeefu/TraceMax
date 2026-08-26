import numpy as np


def sta_lta_ratio(data, nsta, nlta):
    """Compute the STA/LTA ratio for a 1D signal."""
    data = np.asarray(data, dtype=float)
    n = len(data)
    
    nsta = max(1, int(nsta))
    nlta = max(1, int(nlta))
    
    if n < nsta:
        return np.zeros(n)

    # CRITICAL: Remove DC bias
    data = data - np.mean(data)
    power = data ** 2
    
    # Pad power on the left so we can compute full LTA windows from index 0.
    # We use the median of the first nlta samples as the padding noise level.
    pad_len = nlta
    pad_val = np.median(power[:nlta]) if n >= nlta else 0.0
    padded_power = np.pad(power, (pad_len, 0), mode='constant', constant_values=pad_val)
    
    # Cumulative sum of padded power
    csum = np.cumsum(padded_power)
    csum = np.insert(csum, 0, 0.0)
    
    ratio = np.zeros(n)
    
    # A robust epsilon (e.g. 5% of median peak power) to prevent tiny noise from spiking
    epsilon = np.max(power) * 1e-4 + 1e-12

    for i in range(n):
        idx = i + pad_len
        
        # LTA uses a full nlta-length sliding window thanks to padding
        lta = (csum[idx + 1] - csum[idx + 1 - nlta]) / nlta
        
        # STA uses nsta-length sliding window
        sta_start = idx + 1 - nsta
        sta = (csum[idx + 1] - csum[sta_start]) / nsta
        
        ratio[i] = sta / (lta + epsilon)

    return ratio


def pick_first_break(data, timeaxis, nsta, nlta, threshold):
    """Find the first-break arrival using STA/LTA trigger.

    Args:
        data: 1D array of amplitudes.
        timeaxis: 1D array of time values (same length as data).
        nsta: STA window in samples.
        nlta: LTA window in samples.
        threshold: STA/LTA ratio threshold for triggering.

    Returns:
        (sample_index, time_value) or None if no trigger found.
    """
    ratio = sta_lta_ratio(data, nsta, nlta)

    triggered = np.where(ratio >= threshold)[0]
    if len(triggered) == 0:
        return None

    idx = int(triggered[0])
    t0 = timeaxis[0] if len(timeaxis) > 0 else 0.0
    time_val = timeaxis[idx] - t0 if idx < len(timeaxis) else 0.0
    return (idx, time_val)


def ms_to_samples(ms, timeaxis):
    """Convert a duration in milliseconds to sample count."""
    n = len(timeaxis)
    if n < 2:
        return max(1, int(ms))
    dt = (timeaxis[-1] - timeaxis[0]) / (n - 1)
    if dt <= 0:
        return max(1, int(ms))
    return max(1, int((ms / 1000.0) / dt))
