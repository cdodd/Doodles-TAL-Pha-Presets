"""Measure what TAL-Pha's controls really do; writes docs/data/calibration.json."""
import json
import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank
from talalpha import Synth, note

SR = bank.SR
s = Synth(SR)
out = {}
_hp = butter(4, 30, "hp", fs=SR, output="sos")
BASE = {"NumberOfVoices": 0}


def envelope(a, win=220):
    # High-passed first: DCO offset on note start otherwise reads as a long low-level tail.
    m = sosfilt(_hp, a.mean(axis=0))
    n = len(m) // win
    return np.sqrt((m[: n * win].reshape(n, win) ** 2).mean(axis=1)), win / SR


def spectrum(a):
    m = a.mean(axis=0)
    return np.fft.rfftfreq(len(m), 1 / SR), np.abs(np.fft.rfft(m * np.hanning(len(m))))


def resonant_peak(params, pitch=48, velocity=100):
    s.load_params({"DcoWaveSaw": 0, "Noise": 3, "VcfResonance": 0.85, **BASE, **params})
    f, m = spectrum(s.render(note(pitch, 0, 5, velocity), 4))
    return float(f[int(np.argmax(np.convolve(m, np.ones(40) / 40, "same")))])


def harmonics(params, f0=130.81, partials=8):
    s.load_params({**BASE, **params})
    a = s.render(note(48, 0, 3), 2)
    f, m = spectrum(a[:, SR // 2 :])
    peaks = np.array([m[int(np.argmin(np.abs(f - k * f0))) - 3 : int(np.argmin(np.abs(f - k * f0))) + 4].max()
                      for k in range(1, partials + 1)])
    return {"rms": round(float(np.sqrt((a**2).mean())), 3),
            "harmonics_db": np.round(20 * np.log10(peaks / peaks.max() + 1e-6)).astype(int).tolist()}


# Envelope times, EnvKeyFollow 0. Times over 14 s are beyond the render, reported as null.
times = {}
for v in [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8]:
    s.load_params({"EnvAttackTime": v, **BASE})
    r, dt = envelope(s.render(note(48, 0, 20), 10))
    attack = float(np.argmax(r >= 0.9 * r.max()) * dt)
    s.load_params({"EnvDecayTime": v, "EnvSustainLevel": 0, "NoDcOffset": 1, **BASE})
    r, dt = envelope(s.render(note(48, 0, 20), 14))
    peak = int(np.argmax(r))
    decay = float(np.argmax(r[peak:] <= 0.1 * r[peak]) * dt)
    s.load_params({"EnvReleaseTime": v, "NoDcOffset": 1, **BASE})
    r, dt = envelope(s.render(note(48, 0, 0.5), 14))
    release = float(np.argmax(r[int(0.5 / dt) :] <= 0.1 * r[int(0.3 / dt)]) * dt)
    times[v] = {"attack_to_90pct": attack, "decay_to_-20dB": decay, "release_to_-20dB": release}
out["envelope_seconds"] = times

out["cutoff_hz"] = {v: resonant_peak({"VcfCutoff": v}) for v in np.round(np.arange(0, 1.01, 0.1), 1).tolist()}
out["key_follow_cutoff_0.4"] = {v: {"C2_hz": resonant_peak({"VcfCutoff": 0.4, "VcfKeyFollow": v}, 36),
                                    "C4_hz": resonant_peak({"VcfCutoff": 0.4, "VcfKeyFollow": v}, 60)}
                                for v in [0, 0.5, 1]}
out["env_mod_hz_cutoff_0.2"] = {e: resonant_peak({"VcfCutoff": 0.2, "VcfEnvMod": e}) for e in [0, 0.2, 0.4, 0.6, 0.8]}
out["velocity_hz_dynamic_env_0.6"] = {v: resonant_peak({"VcfCutoff": 0.2, "VcfEnvMod": 0.6, "VcfEnvMode": 2}, velocity=v)
                                      for v in [30, 64, 100, 127]}

waves = {}
for w in range(1, 6):
    waves[f"saw{w}"] = harmonics({"DcoWaveSaw": w})
for w in range(1, 5):
    waves[f"pulse{w}"] = harmonics({"DcoWaveSaw": 0, "DcoWavePulse": w, "DcoPwmRate": 0, "DcoPwmDepth": 0.5})
out["waves"] = waves

subs = {}
for w in range(6):
    s.load_params({"DcoWaveSaw": 0, "DcoWaveSub": w, "DcoSubLevel": 3, **BASE})
    f, m = spectrum(s.render(note(48, 0, 3), 2)[:, SR // 2 :])
    level = lambda hz: float(20 * np.log10(m[int(np.argmin(np.abs(f - hz))) - 3 : int(np.argmin(np.abs(f - hz))) + 4].max() + 1e-9))
    subs[w] = {"-2 oct": level(130.81 / 4), "-1 oct": level(130.81 / 2), "note": level(130.81)}
out["sub_wave_levels_db"] = subs

bands = [(30, 60), (60, 120), (120, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 8000)]
hpf, ref = {}, []
for label, params in [("off", {"HpfCutoff": 1}), ("bass_boost", {"HpfCutoff": 0}),
                      ("bass_boost_alt", {"HpfCutoff": 0, "resonanceBoostFrequency": 1}),
                      ("hp1", {"HpfCutoff": 2}), ("hp2", {"HpfCutoff": 3})]:
    s.load_params({"DcoWaveSaw": 0, "Noise": 3, **BASE, **params})
    f, m = spectrum(s.render(note(48, 0, 11), 10))
    vals = [float(20 * np.log10(np.sqrt((m[(f >= lo) & (f < hi)] ** 2).mean()))) for lo, hi in bands]
    ref = ref or vals
    hpf[label] = {f"{lo}-{hi}Hz": round(v - r, 1) for (lo, hi), v, r in zip(bands, vals, ref)}
out["hpf_db_vs_off"] = hpf

# Voices: file value N gives N + 1 voices.
pitches = [48 + 2 * i for i in range(12)]
voices = {}
for v in [0, 1, 3, 5, 11]:
    s.load_params({"NumberOfVoices": v, "DcoWaveSaw": 0, "DcoWavePulse": 1})
    a = s.render(sum((note(p, 0.05 * i, 3) for i, p in enumerate(pitches)), []), 2.5)[:, SR:]
    f, m = spectrum(a)
    voices[v] = int(sum(m[int(np.argmin(np.abs(f - 440 * 2 ** ((p - 69) / 12))))] > 50 * np.median(m) for p in pitches))
out["voices_sounding"] = voices

width = {}
for spread in [0, 0.3, 0.6, 1]:
    s.load_params({"UnisonoVoices": 0.25, "UnisonoDetune": 0.3, "UnisonoSpread": spread, "DcoRange": 2, **BASE})
    a = s.render(note(36, 0, 3), 2.5)
    width[spread] = float(np.sqrt(((a[0] - a[1]) ** 2).mean()) / np.sqrt(((a[0] + a[1]) ** 2).mean()))
out["unison_side_over_mid"] = width

vol = {}
for v in [0.25, 0.5, 1.0]:
    s.load_params({"Volume": v, **BASE})
    vol[v] = float(20 * np.log10(np.sqrt((s.render(note(48, 0, 2), 1.5) ** 2).mean())))
out["volume_rms_db"] = vol

# Arp: pitch sequence from a C4 + E4 + G4 chord per octave-range setting, using host sync (120 BPM here).
arp = {}
for rng in range(4):
    s.load_params({"DcoWaveSaw": 0, "DcoWavePulse": 1, "NumberOfVoices": 5, "arpmode": 1, "arpsyncmode": 2,
                   "arprate": 0.5, "arprange": rng})
    a = s.render(note(60, 0, 3) + note(64, 0, 3) + note(67, 0, 3), 3).mean(axis=0)
    seq = []
    for i in range(0, len(a) - 3528, 882):
        f, m = spectrum(np.stack([a[i : i + 3528]] * 2))
        pitch = int(round(69 + 12 * np.log2(f[int(np.argmax(m[3:])) + 3] / 440)))
        if not seq or seq[-1] != pitch:
            seq.append(pitch)
    arp[rng] = seq[:12]
out["arp_pitches_by_range"] = arp

with open(os.path.join(bank.ROOT, "docs", "data", "calibration.json"), "w") as f:
    json.dump(out, f, indent=1)
for k, v in out.items():
    print(k, json.dumps(v))
