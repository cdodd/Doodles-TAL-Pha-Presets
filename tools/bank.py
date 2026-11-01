"""Shared bank logic: patch data, audition phrases, audio measurements."""
import glob
import os
import tomllib

import numpy as np
from mido import Message
from scipy.signal import butter, find_peaks, lfilter, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = "Doodles"
AUTHOR = "Doodles"
SR = 44100
BEAT = 0.6  # 100 BPM
BAR = 4 * BEAT
ROOTS = [45, 41, 48, 43]  # Am F C G, around A2
TARGET_LUFS = -18.0
PEAK_LIMIT_DB = -3.0
# Test note and held length for single-note measurements, by category.
TEST_NOTE = {"Bass": 45, "Lead": 69, "Pad": 57, "Strings": 57, "Brass": 57, "Arp": 57, "Pluck": 69,
             "Keys and Bells": 60, "Chord and Stab": 57, "FX and Atmosphere": 60}
TEST_HOLD = {"Pad": 5.0, "Strings": 5.0, "FX and Atmosphere": 3.0}
# A common phrase for comparing patches within a category.
COMPARE_PHRASE = {"Bass": "rolling", "Lead": "lead", "Pad": "chords", "Strings": "chords", "Brass": "stabs",
                  "Arp": "arp", "Pluck": "pluck", "Keys and Bells": "keys", "Chord and Stab": "hits",
                  "FX and Atmosphere": "long"}
CHORDS = [[57, 60, 64, 67], [53, 57, 60, 64], [55, 60, 64, 67], [55, 59, 62, 67]]  # Am7 Fmaj7 C G


def load_categories():
    cats = []
    for path in glob.glob(os.path.join(ROOT, "patches", "*.toml")):
        if os.path.basename(path) == "roster.toml":
            continue
        with open(path, "rb") as f:
            data = tomllib.load(f)
        data["slug"] = os.path.splitext(os.path.basename(path))[0]
        cats.append(data)
    order = list(load_roster())
    return sorted(cats, key=lambda c: order.index(c["category"]))


def load_roster():
    with open(os.path.join(ROOT, "patches", "roster.toml"), "rb") as f:
        return tomllib.load(f)


def test_setup(category, patch=None):
    """Returns (MIDI pitch, hold seconds) for single-note measurements."""
    patch = patch or {}
    return patch.get("test_note", TEST_NOTE[category]), patch.get("hold", TEST_HOLD.get(category, 1.5))


def preset_path(category, name):
    return os.path.join(ROOT, "presets", BANK, category, f"{name}.talalpha")


def audio_rel(slug, name):
    return os.path.join("audio", slug, name.lower().replace(" ", "-") + ".mp3")


def _notes(events, beat=BEAT, transpose=0):
    """Events are (start_beats, length_beats, pitch, velocity)."""
    midi = []
    for start, length, pitch, velocity in events:
        midi.append(Message("note_on", note=pitch + transpose, velocity=velocity, time=start * beat))
        midi.append(Message("note_off", note=pitch + transpose, time=(start + length) * beat))
    return sorted(midi, key=lambda m: m.time)


LEAD_LINE = [(0, 1.5, 69), (1.5, .5, 72), (2, 1, 76), (3, 1, 74), (4, 1.5, 72), (5.5, .5, 69), (6, 2, 65),
             (8, 1.5, 67), (9.5, .5, 72), (10, 1, 76), (11, 1, 79), (12, 1.5, 74), (13.5, .5, 71), (14, 2, 67)]
PLUCK_LINE = [69, 72, 76, 79, 76, 72, 69, 72, 65, 69, 72, 76, 72, 69, 65, 69,
              67, 72, 76, 79, 76, 72, 67, 72, 67, 71, 74, 79, 74, 71, 67, 71]


def _chord_events(starts_lengths, velocity=100, bars=range(4)):
    ev = []
    for bar in bars:
        for start, length in starts_lengths:
            ev += [(bar * 4 + start, length, p, velocity - (10 if start % 1 else 0)) for p in CHORDS[bar]]
    return ev


def tempo120_phrase(name):
    """Phrases at 120 BPM, the tempo the plugin sees when rendered outside a host. Returns (events, tail)."""
    roots = [57, 53, 60, 55]
    if name == "lead":
        return [(s, n * 0.92, p, 100) for s, n, p in LEAD_LINE], 2.5
    if name == "legato":
        return [(s, n + 0.08, p, 100) for s, n, p in LEAD_LINE], 2.5
    if name == "chords":
        return _chord_events([(0, 3.9)]), 3.5
    if name == "swells":
        return _chord_events([(0, 7.8)], bars=[0, 2]), 4.0
    if name == "stabs":
        return _chord_events([(0, .4), (1.5, .4), (3, .75)]), 2.0
    if name == "staccato":
        return _chord_events([(i / 2, .22) for i in range(8)]), 2.0
    if name == "arp":
        return _chord_events([(0, 4)]), 2.0
    if name == "pluck":
        return [(i / 2, .4, p, 100 if i % 4 == 0 else 80) for i, p in enumerate(PLUCK_LINE)], 2.5
    if name == "keys":
        return _chord_events([(0, 1.4), (1.5, .4), (2.5, 1.4)]), 2.5
    if name == "hits":
        return [(b * 4 + s, n, roots[b], 105) for b in range(4) for s, n in [(0, .4), (1.5, .4), (3, .75)]], 2.0
    if name == "held":
        return [(b * 4, 3.8, roots[b], 100) for b in range(4)], 3.0
    if name == "long":
        return [(0, 14, 60, 100)], 3.0
    if name == "hits_low":
        return [(i * 4, .4, 48, 110) for i in range(4)], 3.0
    if name == "hits_high":
        return [(i * 2, .3, 72, 105) for i in range(8)], 2.5
    return None


def phrase(name, transpose=0):
    """Returns (midi, seconds including tail)."""
    new = tempo120_phrase(name)
    if new:
        events, tail = new
        seconds = max(s + n for s, n, _, _ in events) * 0.5 + tail
        return _notes(events, 0.5, transpose), seconds
    ev = []
    for bar, root in enumerate(ROOTS):
        t = bar * 4
        if name == "rolling":
            ev += [(t + i / 2, 0.42, root, 115 if i % 4 == 0 else 72 if i % 2 else 92) for i in range(8)]
        elif name == "octaves":
            ev += [(t + i / 2, 0.42, root + (12 if i % 2 else 0), 105 if i % 2 == 0 else 90) for i in range(8)]
        elif name == "sixteenths":
            ev += [(t + i / 4, 0.2, root + (12 if i % 8 == 7 else 0), 105) for i in range(16)]
        elif name == "funk":
            ev += [(t + s / 4, n / 4, root + o, v) for s, n, o, v in [
                (0, 2, 0, 120), (3, 1, 0, 50), (4, 1, 12, 110), (6, 1, 0, 60), (7, 1, 0, 100),
                (10, 1, 0, 115), (11, 1, 3, 55), (12, 2, 7, 105), (14, 1, 12, 112), (15, 1, 10, 60)]]
        elif name == "slides":
            ev += [(t, 1.6, root, 105), (t + 1.5, 0.5, root + 7, 100), (t + 2, 1.1, root + 12, 105),
                   (t + 3, 1.05, root, 100)]
        elif name == "sustained":
            ev.append((t, 3.9, root, 95))
        else:
            raise ValueError(name)
    return _notes(ev, BEAT, transpose), 4 * BAR + 1.5


def _biquad(b0, b1, b2, a0, a1, a2, x):
    return lfilter([b0 / a0, b1 / a0, b2 / a0], [1, a1 / a0, a2 / a0], x, axis=-1)


def lufs(audio):
    """BS.1770 integrated loudness, for stereo audio shaped (2, n)."""
    # K-weighting: high shelf then high-pass, per the published filter design.
    w = 2 * np.pi * 1681.97 / SR
    gain = 10 ** (3.9998 / 40)
    alpha = np.sin(w) / (2 * 0.7072)
    x = _biquad(gain * ((gain + 1) + (gain - 1) * np.cos(w) + 2 * np.sqrt(gain) * alpha),
                -2 * gain * ((gain - 1) + (gain + 1) * np.cos(w)),
                gain * ((gain + 1) + (gain - 1) * np.cos(w) - 2 * np.sqrt(gain) * alpha),
                (gain + 1) - (gain - 1) * np.cos(w) + 2 * np.sqrt(gain) * alpha,
                2 * ((gain - 1) - (gain + 1) * np.cos(w)),
                (gain + 1) - (gain - 1) * np.cos(w) - 2 * np.sqrt(gain) * alpha, audio)
    w = 2 * np.pi * 38.13 / SR
    alpha = np.sin(w) / (2 * 0.5003)
    x = _biquad((1 + np.cos(w)) / 2, -(1 + np.cos(w)), (1 + np.cos(w)) / 2,
                1 + alpha, -2 * np.cos(w), 1 - alpha, x)
    block, hop = int(0.4 * SR), int(0.1 * SR)
    power = (x**2).sum(axis=0)
    energies = np.array([power[i : i + block].mean() for i in range(0, len(power) - block, hop)])
    energies = energies[energies > 10 ** (-70 / 10) / 10 ** (-0.691 / 10)]
    if not len(energies):
        return -99.0
    rel = 10 ** ((-0.691 + 10 * np.log10(energies.mean()) - 10) / 10) / 10 ** (-0.691 / 10)
    return float(-0.691 + 10 * np.log10(energies[energies > rel].mean()))


_hp30 = butter(4, 30, "hp", fs=SR, output="sos")
_lp150 = butter(4, 150, "lp", fs=SR, output="sos")


def _rms(x):
    return float(np.sqrt((x**2).mean()))


def _centroid(mono):
    """Amplitude-weighted spectral centroid in Hz."""
    if len(mono) < 512 or _rms(mono) < 1e-5:
        return 0.0
    mag = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    freqs = np.fft.rfftfreq(len(mono), 1 / SR)
    return float((freqs * mag).sum() / mag.sum())


def _db(x):
    return float(20 * np.log10(max(x, 1e-9)))


def measure_phrase(a):
    """Measurements of a whole audition phrase, shaped (2, n)."""
    x = sosfilt(_hp30, a, axis=1)
    mid, side = (x[0] + x[1]) / 2, (x[0] - x[1]) / 2
    low = sosfilt(_lp150, x, axis=1)
    lmid, lside = (low[0] + low[1]) / 2, (low[0] - low[1]) / 2
    return {
        "lufs": lufs(a),
        "peak_db": _db(np.abs(a).max()),
        "centroid_hz": _centroid(mid),
        "low_energy_pct": 100 * _rms(lmid) ** 2 / max(_rms(mid) ** 2, 1e-12),
        "side_mid": _rms(side) / max(_rms(mid), 1e-9),
        "low_side_mid": _rms(lside) / max(_rms(lmid), 1e-9),
        "mono_loss_db": lufs(np.stack([(a[0] + a[1]) / 2] * 2)) - lufs(a),
    }


def fingerprint(a):
    """Level over time in log bands, plus stereo width over time, for spotting near-duplicates.

    Time matters: arps with similar average spectra can play very different patterns.
    """
    x = sosfilt(_hp30, a, axis=1)
    mid, side = (x[0] + x[1]) / 2, (x[0] - x[1]) / 2
    win = int(0.125 * SR)
    edges = np.geomspace(30, 16000, 25)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    masks = [(freqs >= lo) & (freqs < hi) for lo, hi in zip(edges, edges[1:])]
    frames = []
    for i in range(0, len(mid) - win, win):
        spec = np.abs(np.fft.rfft(mid[i : i + win] * np.hanning(win))) ** 2
        side_level = (side[i : i + win] ** 2).sum()
        frames.append([spec[m].sum() for m in masks] + [side_level / max((mid[i : i + win] ** 2).sum(), 1e-12) * spec.sum()])
    frames = np.array(frames)
    return 10 * np.log10(frames / frames.sum() + 1e-7)


def notes_per_second(a):
    """Rate of distinct level peaks in a phrase, to confirm that an arp is really running."""
    mono = sosfilt(_hp30, a.mean(axis=0))
    win = 220
    n = len(mono) // win
    env = np.sqrt((mono[: n * win].reshape(n, win) ** 2).mean(axis=1))
    peaks, _ = find_peaks(env, prominence=0.15 * env.max(), distance=8)
    return len(peaks) / (len(mono) / SR)


def pitch_spread(a):
    """Range of the main partial in cents, ignoring jumps to other partials."""
    m = a.mean(axis=0)
    win, track = 4096, []
    freqs = np.fft.rfftfreq(1 << 16, 1 / SR)
    band = (freqs > 60) & (freqs < 3000)
    for i in range(0, len(m) - win, 1024):
        mag = np.abs(np.fft.rfft(m[i : i + win] * np.hanning(win), 1 << 16))
        track.append(freqs[band][int(np.argmax(mag[band]))])
    if not track:
        return 0.0
    cents = 1200 * np.log2(np.array(track) / np.median(track))
    cents = cents[np.abs(cents) < 300]
    return float(np.percentile(cents, 95) - np.percentile(cents, 5))


def measure_response(render_note, render_wheel, repeats=10, render_touch=None):
    """Velocity, mod-wheel and aftertouch behaviour, from callables returning one note's audio.

    Interleaved and repeated because unison and chorus run free, so single renders
    differ by a couple of dB. `vel_level_noise` is the standard error of that difference.
    """
    mono = lambda a: sosfilt(_hp30, a.mean(axis=0))
    bright = lambda a: _centroid(mono(a)[int(0.005 * SR) : int(0.15 * SR)])
    level = lambda a: _db(_rms(mono(a)[: int(0.3 * SR)]))

    def held(a):
        # Short notes have gone silent by the held section, so fall back to the note's start.
        x = mono(a)
        late = x[int(0.5 * SR) : int(1.2 * SR)]
        return _centroid(late if _rms(late) > 0.03 * _rms(x[: int(0.3 * SR)]) else x[int(0.01 * SR) : int(0.2 * SR)])

    soft, hard = [], []
    for _ in range(repeats):
        soft.append(render_note(40))
        hard.append(render_note(120))
    soft_levels, hard_levels = [level(a) for a in soft], [level(a) for a in hard]
    wheel_up, wheel_down = render_wheel(127), render_wheel(0)
    result = {
        "vel_bright_ratio": float(np.mean([bright(a) for a in hard]) / max(np.mean([bright(a) for a in soft]), 1)),
        "vel_level_db": float(np.mean(hard_levels) - np.mean(soft_levels)),
        "vel_level_noise": float(np.sqrt((np.var(hard_levels) + np.var(soft_levels)) / repeats)),
        "mw_bright_ratio": held(wheel_up) / max(held(wheel_down), 1),
        "mw_vibrato_cents": pitch_spread(wheel_up[:, int(0.5 * SR) :]) - pitch_spread(wheel_down[:, int(0.5 * SR) :]),
    }
    if render_touch:
        result["at_bright_ratio"] = held(render_touch(127)) / max(held(render_touch(0)), 1)
    return result


def measure_note(a, note_hz, hold=1.5):
    """Measurements of a single held note, shaped (2, n)."""
    mono = sosfilt(_hp30, a.mean(axis=0))
    win = 220
    n = len(mono) // win
    env = np.sqrt((mono[: n * win].reshape(n, win) ** 2).mean(axis=1))
    dt = win / SR
    early = _centroid(mono[int(0.01 * SR) : int(0.06 * SR)])
    late_start, late_end = int(hold * 0.533 * SR), int(hold * 0.867 * SR)
    late = _centroid(mono[late_start:late_end])
    level_late = _rms(mono[late_start:late_end])
    # Strongest spectral peak in the sustained part.
    seg = a.mean(axis=0)[int(hold / 3 * SR) : int(hold * 0.967 * SR)]
    short_note = _rms(seg) < 0.1 * env.max()  # it has already died away, leaving at most some reverb
    if short_note:
        seg = a.mean(axis=0)[int(0.02 * SR) : int(0.25 * SR)]
    mag = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 1 << 18))
    freqs = np.fft.rfftfreq(1 << 18, 1 / SR)
    band = (freqs > note_hz / 4 * 0.9) & (freqs < 4000)  # below this is only residual DC
    f = freqs[band][int(np.argmax(mag[band]))]
    # Tuning: partials should land on the harmonic series of the note's lowest possible
    # periodicity. Oscillator sync repeats at the sub oscillator's rate, so test 1/8 of the note.
    base = note_hz / 8
    # Smoothed over 50 ms, so unison beating doesn't count as decay. None means it holds until note-off.
    smooth = np.convolve(env, np.ones(10) / 10, "same")
    peak = int(np.argmax(smooth))
    fallen = np.where(smooth[peak : int(hold / dt)] < 0.1 * smooth[peak])[0]
    return {
        "attack_s": float(np.argmax(env >= 0.5 * env.max()) * dt),
        "decay_s": float(fallen[0] * dt) if len(fallen) else None,
        "sweep_octaves": float(np.log2(max(early, 1) / max(late, 1))) if late else 0.0,
        "sustain_db": _db(level_late / max(env.max(), 1e-9)),
        "strongest_hz": float(f),
        "cents_off": float(1200 * np.log2(f / (base * round(f / base)))) if f > 0 else 0.0,
        "dc": float(a.mean()),
        "short_note": bool(short_note),
    }
