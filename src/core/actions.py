import numpy as np


# ---------------------------------------------------------------------------
# Selection helpers
# ---------------------------------------------------------------------------

def select_trace(canvas):
    """Toggle selection of the trace under the indicator cursor."""
    for trc in canvas.traces:
        iy = canvas.indicator[1]
        if iy > trc.pos[1] and iy < trc.pos[1] + trc.dim[1]:
            trc.selected = not trc.selected

    canvas.selected = [t for t in canvas.traces if t.selected]
    canvas.once = True
    canvas.repaint()
    canvas.master.sync_info()


def select_all(canvas):
    for trc in canvas.traces:
        trc.selected = True
    canvas.selected = list(canvas.traces)
    canvas.once = True
    canvas.repaint()


def clear_selection(canvas):
    for trc in canvas.selected:
        trc.selected = False
    canvas.selected = []
    canvas.master.sync_info()
    canvas.once = True
    canvas.repaint()


# ---------------------------------------------------------------------------
# Order / visibility
# ---------------------------------------------------------------------------

def move_up(canvas):
    if not canvas.selected:
        return
    nt = len(canvas.traces)
    tmp = [None] * nt
    tid = [t for t in range(nt) if canvas.traces[t].selected]

    if tid[0] == 0:
        return

    for t in tid:
        tmp[t - 1] = canvas.traces[t]
        canvas.traces[t] = None

    ri = 0
    for t in range(nt):
        if canvas.traces[t] is None:
            continue
        while tmp[ri] is not None:
            ri += 1
        tmp[ri] = canvas.traces[t]

    canvas.traces = tmp
    canvas.arrangeTraces()
    canvas.once = True
    canvas.repaint()


def move_down(canvas):
    if not canvas.selected:
        return
    nt = len(canvas.traces)
    tmp = [None] * nt
    tid = [t for t in range(nt) if canvas.traces[t].selected]

    if tid[-1] == nt - 1:
        return

    for t in tid:
        tmp[t + 1] = canvas.traces[t]
        canvas.traces[t] = None

    ri = 0
    for t in range(nt):
        if canvas.traces[t] is None:
            continue
        while tmp[ri] is not None:
            ri += 1
        tmp[ri] = canvas.traces[t]

    canvas.traces = tmp
    canvas.arrangeTraces()
    canvas.once = True
    canvas.repaint()


def delete_trace(canvas):
    if not canvas.selected:
        return
    idtodel = sorted(
        [t for t in range(len(canvas.traces)) if canvas.traces[t].selected],
        reverse=True
    )
    for i in idtodel:
        if len(canvas.traces) > 1:
            canvas.traces.pop(i)
    canvas.arrangeTraces()
    canvas.once = True
    canvas.repaint()


def sequence_names(canvas):
    for i, trc in enumerate(canvas.traces):
        trc.name = 'Trace %02d' % i
    clear_selection(canvas)
    canvas.master.sync_info()
    canvas.once = True
    canvas.repaint()


# ---------------------------------------------------------------------------
# Data editing
# ---------------------------------------------------------------------------

def mute_block(canvas):
    ia, ib = _get_block_range(canvas)
    targets = canvas.selected if canvas.selected else canvas.traces
    for trc in targets:
        d = np.asarray(trc.data)
        d[ia:ib + 1] = 0.0
        trc.data = d if isinstance(trc.data, np.ndarray) else d.tolist()
        trc.dirty = True
    canvas.normalize()
    canvas.once = True
    canvas.repaint()


def cut_block(canvas):
    ia, ib = _get_block_range(canvas)
    nc = ib - ia
    canvas.timeaxis = canvas.timeaxis[:-nc]
    tmax = canvas.timeaxis[-1] - canvas.timeaxis[0]
    for trc in canvas.traces:
        for _ in range(ib - ia):
            trc.data.pop(ia)
        trc.dirty = True
        trc.tmax = tmax
    canvas.once = True
    canvas.repaint()


def stack_traces(canvas):
    tid = [i for i, t in enumerate(canvas.traces) if t.selected]
    if len(tid) < 2:
        return

    stack = np.array([np.asarray(canvas.traces[t].data, dtype=float) for t in tid])
    data = np.mean(stack, axis=0)

    tid.sort(reverse=True)
    for i in tid[:-1]:
        canvas.traces.pop(i)

    keep = tid[-1]
    canvas.traces[keep].data = data.tolist()
    canvas.traces[keep].name = 'stack-%02d' % canvas.nstack
    canvas.traces[keep].dirty = True

    canvas.arrangeTraces()
    canvas.once = True
    canvas.repaint()
    canvas.nstack += 1


# ---------------------------------------------------------------------------
# Pick
# ---------------------------------------------------------------------------

def pick(canvas):
    lt = len(canvas.traces)
    dw = canvas.height() - 30

    # Use visible trace count for lane height when zoomed
    if canvas.trace_view_count > 0 and canvas.trace_view_count < lt:
        visible_count = canvas.trace_view_count
        offset = canvas.trace_view_offset
    else:
        visible_count = lt
        offset = 0

    pw = dw / visible_count

    ix = int(canvas.indicator[1] / pw)
    iy = canvas.getTimeLimit()
    tp = iy[0] + (iy[1] - iy[0]) * canvas.indicator[0] / canvas.width()

    if ix >= visible_count:
        ix = visible_count - 1

    # Map visible slot back to actual trace index
    actual_ix = offset + ix
    if actual_ix >= lt:
        actual_ix = lt - 1

    tt = int(len(canvas.timeaxis) * tp / (canvas.timeaxis[-1] - canvas.timeaxis[0]))
    canvas.traces[actual_ix].pickpoint = tt
    canvas.traces[actual_ix].picktime = tp

    if canvas.pick_function is not None:
        canvas.pick_function((actual_ix, tp))

    canvas.once = True
    canvas.repaint()


def clear_pick(canvas):
    for trc in canvas.traces:
        trc.pickpoint = -1
    canvas.once = True
    canvas.repaint()


def get_all_picks(canvas):
    """Return list of (trace_index, trace_name, picktime) for all picked traces."""
    picks = []
    for i, trc in enumerate(canvas.traces):
        if trc.pickpoint >= 0:
            picks.append((i, trc.name, trc.picktime))
    return picks


def clear_single_pick(canvas, trace_index):
    """Clear pick on a single trace by index."""
    if 0 <= trace_index < len(canvas.traces):
        canvas.traces[trace_index].pickpoint = -1
        canvas.traces[trace_index].picktime = 0.0
        canvas.once = True
        canvas.repaint()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_block_range(canvas):
    if 'end' not in canvas.block:
        return 0, 0
    bb = canvas.block
    a = min(bb['begin'], bb['end'])
    b = max(bb['begin'], bb['end'])
    ltx = canvas.plotlimit[1] - canvas.plotlimit[0]
    ia = ltx * a // canvas.width()
    ib = ltx * b // canvas.width()
    return ia, ib
