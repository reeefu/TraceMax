import numpy as np
import scipy.signal

WINDOW_LENGTH = 200
SAMPLE_RATE = 616.0


def bandpass_filter(trace, lowcut=5.0, highcut=120.0, fs=SAMPLE_RATE, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    if high >= 1.0:
        high = 0.99
    sos = scipy.signal.butter(order, [low, high], btype='band', output='sos')
    return scipy.signal.sosfiltfilt(sos, trace)


def preprocess_trace(amplitude, window_length=WINDOW_LENGTH):
    if len(amplitude) >= window_length:
        trace = amplitude[:window_length].copy()
    else:
        trace = np.zeros(window_length, dtype=np.float64)
        trace[: len(amplitude)] = amplitude

    trace = trace - trace[0]
    trace = bandpass_filter(trace, lowcut=5.0, highcut=120.0, fs=SAMPLE_RATE)

    mean = np.mean(trace)
    std = np.std(trace)
    if std > 1e-10:
        trace = (trace - mean) / std
    else:
        trace = trace - mean

    tmin, tmax = trace.min(), trace.max()
    if tmax - tmin > 1e-10:
        trace = 2.0 * (trace - tmin) / (tmax - tmin) - 1.0

    return trace
