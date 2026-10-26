RSI_N = 5
STRONG, WEAK = 70, 30
BG_STRONG, BG_WEAK = '#fbe0e4', '#dcf1fa'


def simple_rsi(closes, n=RSI_N):
    out = [None] * len(closes)
    for i in range(n, len(closes)):
        diffs = [closes[j] - closes[j - 1] for j in range(i - n + 1, i + 1)]
        gain = sum(d for d in diffs if d > 0) / n
        loss = -sum(d for d in diffs if d < 0) / n
        out[i] = 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    return out


def state(v):
    if v is None:
        return None
    if v >= STRONG:
        return '강세'
    if v <= WEAK:
        return '약세'
    return '중립'


def latest(closes, dates):
    v = simple_rsi(closes)[-1]
    return {'value': round(v, 1), 'state': state(v), 'date': dates[-1]}


def shade(ax, rsi):
    runs = []
    for k, v in enumerate(rsi):
        s = state(v)
        if s not in ('강세', '약세'):
            continue
        if runs and runs[-1][2] == s and runs[-1][1] == k - 1:
            runs[-1][1] = k
        else:
            runs.append([k, k, s])
    for start, end, s in runs:
        color = BG_STRONG if s == '강세' else BG_WEAK
        ax.axvspan(start - 0.5, end + 0.5, color=color, lw=0, zorder=0)
