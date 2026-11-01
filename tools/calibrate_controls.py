"""Measure the controls calibrate.py doesn't reach; writes docs/data/calibration_controls.json.

Run with section names to re-measure only those, e.g. `calibrate_controls.py lfo delay`.
"""
import json
import os
import sys

import numpy as np
from mido import Message
from scipy.signal import butter, hilbert, sosfilt, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank
from talalpha import Synth, note

SR = bank.SR
s = Synth(SR)
PATH = os.path.join(bank.ROOT, "docs", "data", "calibration_controls.json")
_hp = butter(4, 20, "hp", fs=SR, output="sos")
BASE = {"NumberOfVoices": 0, "ModWheelDcoLfo": 0}
TONE = {**BASE, "VcfCutoff": 0.65}  # Filter tames the upper harmonics so the pitch tracker locks on.


def display(attr, param, values, **extra):
    out = {}
    for v in values:
        s.load_params({**extra, attr: v})
        out[str(v)] = s.plugin.parameters[param].string_value
    return out


def mono(a):
    return sosfilt(_hp, a.mean(axis=0))


def rms_db(x):
    return float(20 * np.log10(np.sqrt(np.mean(np.asarray(x) ** 2)) + 1e-9))


def envelope(x, win=220):
    n = len(x) // win
    return np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(axis=1)), win / SR


def spectrum(x):
    return np.fft.rfftfreq(len(x), 1 / SR), np.abs(np.fft.rfft(x * np.hanning(len(x))))


def centroid(x):
    f, m = spectrum(x)
    return float((f * m).sum() / (m.sum() + 1e-12))


def side_mid(a):
    return float(np.sqrt(((a[0] - a[1]) ** 2).mean()) / (np.sqrt(((a[0] + a[1]) ** 2).mean()) + 1e-12))


def pitch_track(x, f0, win=4096, hop=441, span=1.5):
    """Cents from f0 over time, searching a band around it with a zero-padded FFT."""
    h = np.hanning(win)
    f = np.fft.rfftfreq(win * 4, 1 / SR)
    band = (f > f0 / span) & (f < f0 * span)
    idx = np.where(band)[0]
    out = []
    for i in range(0, len(x) - win, hop):
        m = np.abs(np.fft.rfft(x[i : i + win] * h, win * 4))[band]
        k = int(np.argmax(m))
        if 0 < k < len(m) - 1:
            a, b, c = np.log(m[k - 1 : k + 2] + 1e-12)
            k_f = idx[k] + 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
        else:
            k_f = idx[k]
        out.append(1200 * np.log2(max(k_f * SR / (win * 4), 1) / f0))
    return np.array(out), hop / SR


def main_freq(curve, dt):
    c = curve - curve.mean()
    f = np.fft.rfftfreq(len(c) * 8, dt)
    m = np.abs(np.fft.rfft(c * np.hanning(len(c)), len(c) * 8))
    return float(f[1 + int(np.argmax(m[1:]))])


def res_peak(x):
    f, m = spectrum(x)
    keep = (f > 20) & (f < 18000)
    return float(f[keep][int(np.argmax(np.convolve(m, np.ones(40) / 40, "same")[keep]))])


def resonant(params, midi=None, dur=4, skip=1.0):
    s.load_params({**BASE, "DcoWaveSaw": 0, "Noise": 3, "VcfResonance": 0.85, **params})
    return res_peak(s.render(midi or note(48, 0, dur + 1), dur)[:, int(skip * SR) :].mean(axis=0))


C3, C4 = 130.81, 261.63
UNIT = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]


def lfo():
    out = {"rate_panel_hz": display("LfoRate", "lfo_rate", UNIT), "delay_panel_s": display("LfoDelay", "lfo_delay", UNIT)}
    # Real rate, read from the vibrato on a held note.
    rate = {}
    for v in [0.3, 0.5, 0.7, 0.8]:
        s.load_params({**TONE, "LfoRate": v, "DcoLfoMod": 0.3})
        c, dt = pitch_track(mono(s.render(note(60, 0, 13), 12))[SR // 4 :], C4, win=2048 if v > 0.6 else 4096)
        rate[v] = round(main_freq(c, dt), 2)
    out["rate_measured_hz"] = rate
    # Waveform: a slow LFO on pitch shows the shape directly.
    shapes = {}
    for w in range(6):
        s.load_params({**TONE, "LfoRate": 0.5, "DcoLfoMod": 0.4, "LfoWaveform": w})
        c, dt = pitch_track(mono(s.render(note(60, 0, 9), 8))[SR // 4 :], C4)
        d = np.diff(c)
        shapes[w] = {"name": display("LfoWaveform", "lfo_waveform", [w])[str(w)],
                     "min_cents": round(float(np.percentile(c, 2))), "max_cents": round(float(np.percentile(c, 98))),
                     "still_frames": round(float((np.abs(d) < 1).mean()), 2),
                     "rising_frames": round(float((d > 1).mean()), 2), "falling_frames": round(float((d < -1).mean()), 2)}
    out["waveforms"] = shapes
    # Invert: saw direction flips.
    s.load_params({**TONE, "LfoRate": 0.5, "DcoLfoMod": 0.4, "LfoWaveform": 2, "LfoInvert": 1})
    c, _ = pitch_track(mono(s.render(note(60, 0, 9), 8))[SR // 4 :], C4)
    d = np.diff(c)
    out["inverted_saw"] = {"rising_frames": round(float((d > 1).mean()), 2), "falling_frames": round(float((d < -1).mean()), 2)}
    # Delay: when the vibrato arrives on a fresh note, on pitch and on filter.
    arrive = {}
    for v in [0.4, 0.5, 0.6, 0.7]:
        s.load_params({**TONE, "LfoRate": 0.7, "DcoLfoMod": 0.3, "LfoDelay": v, "LfoTrigger": 1})
        c, dt = pitch_track(mono(s.render(note(60, 0, 11), 10)), C4, win=2048)
        n = int(0.4 / dt)
        depth = np.array([np.ptp(c[i : i + n]) for i in range(0, len(c) - n, n // 4)])
        full = np.median(depth[-8:])
        t = lambda frac: float(np.argmax(depth >= frac * full) * n // 4 * dt)
        arrive[v] = {"to_10pct_s": round(t(0.1), 2), "to_90pct_s": round(t(0.9), 2), "full_cents": round(float(full))}
    out["delay_arrival"] = arrive
    s.load_params({**BASE, "VcfCutoff": 0.5, "LfoRate": 0.7, "VcfLfoMod": 0.6, "LfoDelay": 0.7, "LfoTrigger": 1})
    r, dt = envelope(mono(s.render(note(60, 0, 6), 5)), 882)
    r = 20 * np.log10(r + 1e-6)
    out["delay_on_filter_swing_db"] = {"0.2-1.5s": round(float(np.ptp(r[int(0.2 / dt) : int(1.5 / dt)])), 1), "3.5-4.5s": round(float(np.ptp(r[int(3.5 / dt) : int(4.5 / dt)])), 1)}
    # Trigger: pitch offset at the start of repeated notes.
    trig = {}
    for t in [0, 1]:
        s.load_params({**TONE, "LfoRate": 0.5, "DcoLfoMod": 0.4, "LfoTrigger": t, "EnvReleaseTime": 0})
        starts = []
        for i, gap in enumerate([0.37, 0.61, 0.83, 1.13, 1.57, 0.71]):
            at = sum([0.37, 0.61, 0.83, 1.13, 1.57, 0.71][:i])
            starts.append(at)
        midi = sum((note(60, at, at + 0.3) for at in starts), [])
        x = mono(s.render(midi, 6))
        c, dt = pitch_track(x, C4, win=2048)
        trig[t] = [round(float(c[int((at + 0.05) / dt)])) for at in starts]
    out["trigger_start_cents"] = trig
    noise = {}
    for v in [0.2, 0.5, 0.7]:
        s.load_params({**BASE, "VcfCutoff": 0.5, "LfoRate": v, "LfoWaveform": 5, "VcfLfoMod": 0.6})
        r, dt = envelope(mono(s.render(note(60, 0, 11), 10))[SR // 2 :], 2205)
        r = 20 * np.log10(r + 1e-6)
        s.load_params({**BASE, "VcfCutoff": 0.5, "LfoRate": v, "LfoWaveform": 0, "VcfLfoMod": 0.6})
        q, _ = envelope(mono(s.render(note(60, 0, 11), 10))[SR // 2 :], 2205)
        q = 20 * np.log10(q + 1e-6)
        noise[v] = {"noise_swing_db": round(float(np.ptp(r)), 1), "triangle_swing_db": round(float(np.ptp(q)), 1)}
    out["noise_wave_on_filter"] = noise
    # Sync: what the rate control shows, then the real rate at 120 BPM.
    out["sync_rate_panel"] = display("LfoRate", "lfo_rate", [round(0.05 * i, 2) for i in range(21)], LfoSync=1)
    synced = {}
    for v in [0.2, 0.4, 0.5, 0.6, 0.8]:
        s.load_params({**TONE, "LfoSync": 1, "LfoRate": v, "DcoLfoMod": 0.3})
        c, dt = pitch_track(mono(s.render(note(60, 0, 13), 12))[SR // 4 :], C4, win=2048)
        synced[v] = {"panel": s.plugin.parameters["lfo_rate"].string_value, "hz": round(main_freq(c, dt), 2)}
    out["sync_measured"] = synced
    # Filter LFO depth in octaves, using a slow square LFO so the cutoff sits at each extreme.
    depth = {}
    for v in [0.1, 0.2, 0.4, 0.6, 1.0]:
        s.load_params({**BASE, "DcoWaveSaw": 0, "Noise": 3, "VcfResonance": 0.85, "VcfCutoff": 0.5, "LfoRate": 0.4,
                       "LfoWaveform": 3, "VcfLfoMod": v})
        x = s.render(note(48, 0, 11), 10).mean(axis=0)
        peaks = [res_peak(x[i : i + SR // 4]) for i in range(0, len(x) - SR // 4, SR // 4)]
        depth[v] = {"low_hz": round(float(np.percentile(peaks, 10))), "high_hz": round(float(np.percentile(peaks, 90)))}
    out["vcf_lfo_square_cutoff_470hz"] = depth
    return out


def at_render(params, pressure, pitch=60, dur=4, kind="aftertouch"):
    s.load_params(params)
    kw = {"value": pressure} if kind == "aftertouch" else {"note": pitch, "value": pressure}
    return s.render(note(pitch, 0.01, dur + 1) + [Message(kind, time=0.03, **kw)], dur)


def performance():
    out = {}
    # DCO aftertouch adds to the LFO amount.
    dco = {}
    for v in [0.25, 0.5, 1.0]:
        p = {**TONE, "LfoRate": 0.7, "DcoAtMod": v}
        row = {}
        for at in [0, 64, 127]:
            c, _ = pitch_track(mono(at_render(p, at))[SR // 2 :], C4, win=2048)
            row[at] = round(float(np.percentile(c, 98) - np.percentile(c, 2)))
        dco[v] = row
    out["dco_at_swing_cents"] = dco
    vcf = {}
    for v in [0.25, 0.5, 1.0]:
        p = {**BASE, "DcoWaveSaw": 0, "Noise": 3, "VcfResonance": 0.85, "VcfCutoff": 0.4, "VcfAftertouch": v}
        vcf[v] = {at: round(res_peak(at_render(p, at)[:, SR:].mean(axis=0))) for at in [0, 64, 127]}
    out["vcf_at_cutoff_hz_from_220"] = vcf
    vca = {}
    for v in [0.25, 0.5, 1.0]:
        p = {**BASE, "VcaLevel": 0.5, "VcaAftertouch": v}
        vca[v] = {at: round(rms_db(at_render(p, at)[:, SR:]), 1) for at in [0, 64, 127]}
    out["vca_at_level_db_from_level_5"] = vca
    p = {**BASE, "DcoWaveSaw": 0, "Noise": 3, "VcfResonance": 0.85, "VcfCutoff": 0.4, "VcfAftertouch": 1}
    out["poly_aftertouch_hz"] = round(res_peak(at_render(p, 127, kind="polytouch")[:, SR:].mean(axis=0)))
    # Bender.
    bend = {}
    for rng in [0, 2, 7, 12]:
        s.load_params({**TONE, "BenderRange": rng})
        row = {}
        for label, value in [("up", 8191), ("down", -8192)]:
            x = mono(s.render(note(60, 0.01, 3) + [Message("pitchwheel", pitch=value, time=0.03)], 2))[SR // 2 :]
            c, _ = pitch_track(x, C4 * 2 ** (rng * (1 if value > 0 else -1) / 12))
            row[label] = round(float(np.median(c)) / 100 + rng * (1 if value > 0 else -1), 2)
        bend[rng] = row
    out["bend_semitones"] = bend
    # Mod wheel to filter cutoff.
    wheel = {}
    for v in [0.1, 0.25, 0.5, 1.0]:
        midi = note(48, 0.01, 5) + [Message("control_change", control=1, value=127, time=0)]
        wheel[v] = round(resonant({"VcfCutoff": 0.3, "ModWheelVcfRange": v}, midi))
    out["wheel_cutoff_hz_from_100"] = wheel
    # Mod wheel to filter LFO: the swing in cutoff with a slow square LFO, wheel full.
    wl = {}
    for v in [0.25, 0.5, 1.0]:
        s.load_params({**BASE, "DcoWaveSaw": 0, "Noise": 3, "VcfResonance": 0.85, "VcfCutoff": 0.5, "LfoRate": 0.4,
                       "LfoWaveform": 3, "ModWheelVcfLfo": v})
        x = s.render(note(48, 0.01, 11) + [Message("control_change", control=1, value=127, time=0)], 10).mean(axis=0)
        peaks = [res_peak(x[i : i + SR // 4]) for i in range(0, len(x) - SR // 4, SR // 4)]
        wl[v] = {"low_hz": round(float(np.percentile(peaks, 10))), "high_hz": round(float(np.percentile(peaks, 90)))}
    out["wheel_vcf_lfo_cutoff_470hz"] = wl
    # Portamento: time to cover 90% of the interval, for two interval sizes, with the time-mode switch.
    glide = {}
    for mode in [0, 1]:
        row = {}
        for v in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
            cell = {}
            for semis in [12, 24]:
                s.load_params({**TONE, "VcfCutoff": 0.8, "PortamentoMode": 2, "PortamentoTime": v, "paramPortamentoTimeMode": mode})
                target = 48 + semis
                x = mono(s.render(note(48, 0, 1.0) + note(target, 1.0, 13), 12))
                f_t = 440 * 2 ** ((target - 69) / 12)
                h = 2048
                cents = []
                for i in range(SR, len(x) - h, 441):
                    z = np.abs(np.fft.rfft(x[i : i + h] * np.hanning(h), h * 4))
                    f = np.fft.rfftfreq(h * 4, 1 / SR)
                    band = (f > 100) & (f < f_t * 1.3)
                    cents.append(1200 * np.log2(f[band][int(np.argmax(z[band]))] / f_t))
                cents = np.array(cents)
                near = np.abs(cents) <= 0.1 * semis * 100
                # Last frame still outside the 90% line, so a stray early hit doesn't count.
                last_out = int(np.where(~near)[0][-1]) if (~near).any() else 0
                cell[semis] = round((last_out + 1) * 441 / SR + h / SR / 2, 3)
            row[v] = cell
        glide[mode] = row
    out["portamento_to_90pct_s"] = glide
    # Velocity to level in the VCA dynamic modes.
    vel = {}
    for mode in [0, 2, 3]:
        s.load_params({**BASE, "VcaEnvMode": mode})
        vel[mode] = {v: round(rms_db(s.render(note(60, 0, 2, v), 1.5)[:, SR // 4 :]), 1) for v in [30, 64, 100, 127]}
    out["vca_velocity_db"] = vel
    return out


def oscillator():
    out = {}
    def level(p):
        s.load_params({**BASE, **p})
        return round(rms_db(s.render(note(48, 0, 2), 1.5)[:, SR // 4 :]), 1)
    out["saw_volume_db"] = {v: level({"specialSawVolume": v}) for v in [0.1, 0.25, 0.5, 0.75, 1.0]}
    out["pulse_volume_db"] = {v: level({"DcoWaveSaw": 0, "DcoWavePulse": 1, "specialPulseVolume": v}) for v in [0.1, 0.25, 0.5, 0.75, 1.0]}
    out["sub_panel"] = display("DcoSubLevel", "dco_sub_level", [0, 1, 2, 3, 4])
    out["noise_panel"] = display("Noise", "dco_noise", [0, 1, 2, 3, 4])
    out["sub_level_db"] = {v: level({"DcoWaveSaw": 0, "DcoWaveSub": 1, "DcoSubLevel": v}) for v in [0.5, 1, 2, 3]}
    out["noise_level_db"] = {v: level({"DcoWaveSaw": 0, "Noise": v}) for v in [0.5, 1, 2, 3]}
    out["vca_level_db"] = {v: level({"VcaLevel": v}) for v in [0.25, 0.5, 0.75, 1.0]}
    out["saw_alone_db"] = level({})
    # PWM: the duty cycle, read from the waveform period by period.
    def duty_curve(p):
        s.load_params({**BASE, "DcoWaveSaw": 0, "NoDcOffset": 1, **p})
        x = s.render(note(36, 0, 13), 12).mean(axis=0)[SR // 2 :]
        x = x - np.convolve(x, np.ones(2000) / 2000, "same")
        per = int(round(SR / 65.41 * 2))
        return np.array([(x[i : i + per] > 0).mean() for i in range(0, len(x) - per, per // 2)]), per / 2 / SR
    pwm = {}
    for w in range(1, 5):
        d, _ = duty_curve({"DcoWavePulse": w, "DcoPwmRate": 0, "DcoPwmDepth": 0})
        e, _ = duty_curve({"DcoWavePulse": w, "DcoPwmRate": 0, "DcoPwmDepth": 0.5})
        pwm[w] = {"panel": display("DcoWavePulse", "dco_wave_pulse", [w])[str(w)], "duty_depth0": round(float(np.median(d)), 3), "duty_depth5": round(float(np.median(e)), 3)}
    out["pulse_duty"] = pwm
    out["pwm_static_duty"] = {v: round(float(np.median(duty_curve({"DcoWavePulse": 3, "DcoPwmRate": 0, "DcoPwmDepth": v})[0])), 3) for v in [0, 0.25, 0.5, 0.75, 1.0]}
    rates = {}
    for v in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        d, dt = duty_curve({"DcoWavePulse": 3, "DcoPwmRate": v, "DcoPwmDepth": 0.6})
        rates[v] = {"hz": round(main_freq(d, dt), 2), "duty_min": round(float(np.percentile(d, 3)), 2), "duty_max": round(float(np.percentile(d, 97)), 2)}
    out["pwm_rate"] = rates
    # Pulse Tune and its modulation. The saw is off, so only the pulse is tracked.
    tracked = lambda p, f0=C4, w=4096: pitch_track(mono((s.load_params({**TONE, "DcoWaveSaw": 0, "DcoWavePulse": 1, **p}), s.render(note(60, 0, 4), 3))[1]), f0, win=w)[0]
    out["pulse_tune_cents"] = {v: round(float(np.median(tracked({"specialPulseTune": v}, C4 * 2 ** (v / 12))) + v * 100)) for v in [-12, 7, 12]}
    out["pulse_fine_panel"] = display("specialPulseFineTune", "pulse_finetune", [-1, -0.5, 0.5, 1])
    out["pulse_fine_cents"] = {v: round(float(np.median(tracked({"specialPulseFineTune": v})))) for v in [-1, -0.5, 0.1, 0.5, 1]}
    out["master_fine_cents"] = {v: round(float(np.median(pitch_track(mono((s.load_params({**TONE, "MasterFineTune": v}), s.render(note(60, 0, 3), 2))[1]), C4)[0]))) for v in [0, 0.25, 0.75, 1]}
    out["pulse_env_panel"] = display("specialPulseDcoEnv", "pulse_dco_env", [-1, -0.5, 0.5, 1])
    env = {}
    for v in [-0.5, 0.1, 0.25, 0.5, 1]:
        s.load_params({**TONE, "VcfCutoff": 0.6, "DcoWaveSaw": 0, "DcoWavePulse": 1, "EnvDecayTime": 0.5, "EnvSustainLevel": 0, "VcaEnvMode": 1, "specialPulseDcoEnv": v})
        c = pitch_track(mono(s.render(note(60, 0, 3), 2.5)), C4, win=1024, hop=220, span=8)[0]
        env[v] = {"start_cents": round(float(np.median(c[1:5]))), "end_cents": round(float(np.median(c[-30:])))}
    out["pulse_env_cents"] = env
    lf = {}
    for v in [-0.25, 0.02, 0.05, 0.1, 0.25, 0.5]:
        s.load_params({**TONE, "VcfCutoff": 0.6, "DcoWaveSaw": 0, "DcoWavePulse": 1, "LfoRate": 0.5, "specialPulseDcoLfo": v})
        c, _ = pitch_track(mono(s.render(note(60, 0, 7), 6))[SR // 4 :], C4, span=8)
        lf[v] = round(float(np.percentile(c, 98) - np.percentile(c, 2)))
    out["pulse_lfo_swing_cents"] = lf
    # Octave and range, read from the display.
    out["octave_panel"] = display("Octave", "octave", [-2, -1, 0, 1, 2])
    out["range_panel"] = display("DcoRange", "dco_range", [0, 1, 2, 3])
    return out


def filt():
    out = {}
    def averaged(p, dur=6):
        s.load_params({**BASE, "DcoWaveSaw": 0, **p})
        x = s.render(note(60, 0, dur + 1), dur).mean(axis=0)[SR // 2 :]
        win = 8192
        m = np.array([np.abs(np.fft.rfft(x[i : i + win] * np.hanning(win))) ** 2 for i in range(0, len(x) - win, win // 2)]).mean(axis=0)
        return np.fft.rfftfreq(win, 1 / SR), m, x
    # Resonance: how far the peak stands above the passband, an octave below it. Noise, so no harmonic lines.
    res = {}
    for boost in [0, 1]:
        row = {}
        for v in [0, 0.25, 0.5, 0.75, 0.9, 1.0]:
            f, m, x = averaged({"Noise": 3, "VcfCutoff": 0.6, "VcfResonance": v, "resonanceBoost": boost})
            m = np.convolve(m, np.ones(7) / 7, "same")
            k = int(np.argmax(m[10:])) + 10
            row[v] = {"peak_hz": round(float(f[k])), "peak_over_octave_below_db": round(float(10 * np.log10(m[k] / m[int(k / 2)]))), "rms_db": round(rms_db(x), 1)}
        res[boost] = row
    out["resonance_noise"] = res
    # Level lost on a real sound as resonance rises.
    lost = {}
    for boost in [0, 1]:
        row = {}
        for v in [0, 0.25, 0.5, 0.75, 1.0]:
            s.load_params({**BASE, "VcfCutoff": 0.55, "VcfResonance": v, "resonanceBoost": boost})
            row[v] = round(rms_db(s.render(note(36, 0, 3), 2.5)[:, SR // 2 :]), 1)
        lost[boost] = row
    out["saw_c2_level_db"] = lost
    # Self-oscillation: silence in, then the faintest noise in.
    selfosc = {}
    for boost in [0, 1]:
        row = {}
        for v in [0.9, 1.0]:
            cell = {}
            for noise in [0, 0.01, 0.05]:
                f, m, x = averaged({"Noise": noise, "VcfCutoff": 0.6, "VcfResonance": v, "resonanceBoost": boost})
                k = int(np.argmax(m[10:])) + 10
                cell[noise] = {"rms_db": round(rms_db(x), 1), "peak_hz": round(float(f[k])), "peak_share": round(float(m[k - 3 : k + 4].sum() / m.sum()), 2)}
            row[v] = cell
        selfosc[boost] = row
    out["self_oscillation"] = selfosc
    return out


def envelope_more():
    out = {}
    follow = {}
    for v in [0, 0.5, 1.0]:
        row = {}
        for pitch in [36, 60, 84]:
            s.load_params({**BASE, "EnvDecayTime": 0.5, "EnvSustainLevel": 0, "EnvKeyFollow": v, "NoDcOffset": 1})
            r, dt = envelope(mono(s.render(note(pitch, 0, 8), 7)), 2205)  # Longer than a C2 period, so ripple doesn't count.
            k = int(np.argmax(r))
            row[pitch] = round(float(np.argmax(r[k:] <= 0.1 * r[k]) * dt), 2)
        follow[v] = row
    out["key_follow_decay_s_t3_5"] = follow
    t2 = {}
    for v in [0.2, 0.3, 0.4, 0.5, 0.6]:
        s.load_params({**BASE, "EnvAttackLevel": 1, "EnvBreakTime": v, "EnvBreakLevel": 0, "EnvDecayTime": 0, "EnvSustainLevel": 0, "NoDcOffset": 1})
        r, dt = envelope(mono(s.render(note(48, 0, 8), 7)))
        k = int(np.argmax(r))
        t2[v] = round(float(np.argmax(r[k:] <= 0.1 * r[k]) * dt), 3)
    out["t2_to_-20dB_s"] = t2
    return out


def chorus():
    out = {"switch_panel": display("DcoChorusSwitch", "chorus_switch", [0, 1, 2, 3])}
    modes = {}
    for mode in [0, 1, 2, 3]:
        row = {}
        for pitch, f0 in [(36, 65.41), (69, 440.0)]:
            s.load_params({**BASE, "DcoChorusSwitch": mode, "VcfCutoff": 0.7})
            a = s.render(note(pitch, 0, 7), 6)[:, SR // 2 :]
            row[pitch] = {"side_mid": round(side_mid(a), 2), "mono_change_db": round(rms_db(a.mean(axis=0)) - rms_db(a[0]), 1)}
        modes[mode] = row
    out["modes"] = modes
    # Rate: no single clean Hz comes out (two lines beat), so report the pitch wobble on one channel of a near-sine.
    band = butter(4, [300, 600], "bp", fs=SR, output="sos")
    rate = {}
    for v in [0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0]:
        s.load_params({**BASE, "DcoChorusSwitch": 1, "ChorusRate": v, "VcfCutoff": 0.45})
        x = sosfiltfilt(band, s.render(note(69, 0, 21), 20)[0, SR:])
        inst = np.diff(np.unwrap(np.angle(hilbert(x)))) * SR / (2 * np.pi)
        inst = inst[: len(inst) // 441 * 441].reshape(-1, 441).mean(axis=1)
        cents = 1200 * np.log2(np.maximum(inst, 1) / 440)
        rate[v] = round(float(np.percentile(cents, 98) - np.percentile(cents, 2)), 1)
    out["left_swing_cents_a4"] = rate
    return out


SETTLE = 4.0  # Effect times glide to a new value after a preset loads, so test notes wait for them.


def blip(extra, dur=6, length=0.05, pitch=60):
    s.load_params({**BASE, "VcaEnvMode": 1, "EnvReleaseTime": 0, "VcfCutoff": 0.75, **extra})
    return s.render(note(pitch, SETTLE, SETTLE + length), SETTLE + dur)[:, int(SETTLE * SR) :]


def echoes(x, dt, floor=-55):
    """Onset times and peak dB of separate echoes in an envelope."""
    db = 20 * np.log10(x + 1e-7)
    out, i = [], 0
    while i < len(db):
        if db[i] > floor:
            j = i
            while j < len(db) and db[j] > floor:
                j += 1
            out.append((round(i * dt, 3), round(float(db[i:j].max()), 1)))
            i = j
        else:
            i += 1
    return out


def delay():
    out = {"time_panel_sync": display("delayTime", "fx_delay_time", [round(i * 0.05, 2) for i in range(21)]),
           "time_panel_free": display("delayTime", "fx_delay_time", UNIT, delaySync=0),
           "mix_panel": display("delayDryWet", "fx_delay_dry_wet", UNIT)}
    fb = {}
    for v in [0.2, 0.4, 0.6, 0.8, 1.0]:
        a = blip({"delayDryWet": 0.8, "delayTime": 0.3, "delayFeedback": v}, dur=8)
        r, dt = envelope(a.mean(axis=0))
        fb[v] = echoes(r, dt)[:8]
    out["feedback_echoes"] = fb
    mix = {}
    for v in [0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]:
        a = blip({"delayDryWet": v, "delayTime": 0.3, "delayFeedback": 0}, dur=2)
        r, dt = envelope(a.mean(axis=0))
        mix[v] = echoes(r, dt)[:3]
    out["mix_dry_and_echo"] = mix
    free = {}
    for v in [0, 0.1, 0.3, 0.5, 0.7, 0.9]:
        r, dt = envelope(blip({"delayDryWet": 1.0, "delayTime": v, "delaySync": 0, "delayFeedback": 0}).mean(axis=0), 44)
        free[v] = echoes(r, dt)[0][0]
    out["free_time_first_echo_s"] = free
    # Effects settle after a preset loads: first echo time, by how long after loading the note starts (0.3 s pre-roll included).
    settle = {}
    for start in [0, 0.25, 0.5, 1, 4]:
        s.load_params({**BASE, "VcaEnvMode": 1, "EnvReleaseTime": 0, "VcfCutoff": 0.75, "delayDryWet": 0.8, "delayTime": 0.3, "delayFeedback": 0})
        r, dt = envelope(s.render(note(60, start, start + 0.05), start + 1.5)[:, int(start * SR) :].mean(axis=0), 44)
        settle[start] = echoes(r, dt)[:4]
    out["echoes_after_load"] = settle
    tone = {}
    for v in [0, 0.25, 0.5, 0.75, 1.0]:
        a = blip({"delayDryWet": 0.8, "delayTime": 0.3, "delayFeedback": 0, "delayTone": v, "VcfCutoff": 1, "Noise": 3}, dur=2)
        e = a[:, int(0.48 * SR) : int(0.62 * SR)].mean(axis=0)
        tone[v] = {"echo_centroid_hz": round(centroid(e)), "echo_db": round(rms_db(e), 1)}
    out["tone"] = tone
    spread = {}
    for v in [0, 0.25, 0.5, 0.55, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0]:
        a = blip({"delayDryWet": 1.0, "delayTime": 0.3, "delayFeedback": 0.9, "delaySpread": v}, dur=5)
        w = [a[:, int(k * 0.5 * SR) : int((k * 0.5 + 0.08) * SR)] for k in range(1, 7)]
        spread[v] = {"left_minus_right_db": [round(rms_db(e[0]) - rms_db(e[1])) for e in w], "side_mid": round(side_mid(a[:, SR // 4 :]), 2)}
    out["spread"] = spread
    return out


def reverb():
    out = {"mix_panel": display("reverbDryWet", "fx_reverb_dry_wet", UNIT)}
    def tail(p):
        a = blip({"reverbDryWet": 0.8, "Noise": 3, **p}, dur=14, length=0.1)
        r, dt = envelope(a.mean(axis=0))
        return a, r, dt
    size = {}
    for v in [0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        a, r, dt = tail({"reverbSize": v})
        i = int(0.15 / dt)
        ref = r[i]
        below = np.where(r[i:] <= 0.01 * ref)[0]
        size[v] = {"to_-40dB_s": round(float(below[0] * dt), 2) if len(below) else None, "tail_db": round(float(20 * np.log10(ref + 1e-7)), 1)}
    out["size_tail"] = size
    pre = {}
    for v in [0, 0.1, 0.2, 0.3, 0.5, 0.7]:
        a = blip({"reverbDryWet": 1.0, "reverbSize": 0.5, "reverbDelay": v}, dur=2, length=0.03)  # Full wet: no dry note to hide it.
        r, dt = envelope(a.mean(axis=0), 22)
        db = 20 * np.log10(r + 1e-7)
        pre[v] = {"panel": display("reverbDelay", "fx_reverb_delay", [v])[str(v)], "first_sound_s": round(float(np.argmax(db > db.max() - 30) * dt), 3)}
    out["predelay"] = pre
    tone = {}
    for v in [0, 0.3, 0.5, 0.7, 1.0]:
        a, r, dt = tail({"reverbTone": v, "reverbSize": 0.6, "VcfCutoff": 1})
        t = a[:, int(0.2 * SR) : int(1.0 * SR)].mean(axis=0)
        tone[v] = {"tail_centroid_hz": round(centroid(t)), "tail_db": round(rms_db(t), 1)}
    out["tone"] = tone
    mix = {}
    for v in [0.3, 0.5, 0.7, 0.8, 0.9, 0.99, 1.0]:
        s.load_params({**BASE, "reverbDryWet": v})
        a = s.render(note(60, SETTLE, SETTLE + 3), SETTLE + 5)[:, int(SETTLE * SR) :]
        mix[v] = {"held_db": round(rms_db(a[:, SR : 2 * SR]), 1), "tail_db": round(rms_db(a[:, int(3.1 * SR) : int(3.6 * SR)]), 1), "held_side_mid": round(side_mid(a[:, SR : 2 * SR]), 2)}
    out["mix"] = mix
    return out


def eq():
    out = {"freq_panel": display("eqBellFreq", "eq_freq", UNIT), "q_panel": display("eqBellQ", "eq_q", UNIT),
           "gain_panel": display("eqBellGain", "eq_gain", [-48, -24, -12, -6, 0, 6, 12, 24, 48])}
    def noise_spec(p):
        s.load_params({**BASE, "DcoWaveSaw": 0, "Noise": 3, **p})
        x = s.render(note(60, 0, 11), 10).mean(axis=0)[SR // 2 :]
        win = 8192
        fr = np.array([np.abs(np.fft.rfft(x[i : i + win] * np.hanning(win))) ** 2 for i in range(0, len(x) - win, win // 2)]).mean(axis=0)
        return np.fft.rfftfreq(win, 1 / SR), fr
    f, ref = noise_spec({})
    bell = {}
    for fv, gain, q in [(0.5, 12, 0.5), (0.5, -12, 0.5), (0.5, 6, 0.5), (0.3, 12, 0.5), (0.7, 12, 0.5), (0.5, 12, 0.3), (0.5, 12, 0.4), (0.5, 12, 0.6), (0.5, 12, 0.7), (0.5, 12, 0.8)]:
        _, m = noise_spec({"eqBellFreq": fv, "eqBellGain": gain, "eqBellQ": q})
        d = 10 * np.log10(m / (ref + 1e-12) + 1e-12)
        k = np.convolve(d, np.ones(5) / 5, "same")
        i = int(np.argmax(np.abs(k[3:-3]))) + 3
        half = np.abs(k) >= abs(k[i]) / 2
        lo = i
        while lo > 0 and half[lo]:
            lo -= 1
        hi = i
        while hi < len(k) - 1 and half[hi]:
            hi += 1
        bell[f"f{fv}/g{gain}/q{q}"] = {"panel_freq": out["freq_panel"][str(fv)], "panel_q": display("eqBellQ", "eq_q", [q])[str(q)],
                                       "peak_hz": round(float(f[i])), "peak_db": round(float(k[i]), 1),
                                       "half_gain_octaves": round(float(np.log2(max(f[hi], 1) / max(f[lo], 1))), 2)}
    out["bell"] = bell
    return out


def voices():
    out = {"unison_panel": display("UnisonoVoices", "unison_voices", [round(i * 0.05, 2) for i in range(21)])}
    VT = lambda **kw: [{**kw}] * 12
    tuned = {}
    for v in [0, 0.25, 0.75, 1]:
        s.load_params(TONE, voice_tuning=VT(detune=v))
        c, _ = pitch_track(mono(s.render(note(60, 0, 3), 2)), C4)
        tuned[v] = round(float(np.median(c)), 1)
    out["vt_detune_cents"] = tuned
    cut = {}
    for v in [0, 0.25, 0.5, 0.75, 1]:
        s.load_params({**BASE, "DcoWaveSaw": 0, "Noise": 3, "VcfResonance": 0.85, "VcfCutoff": 0.5}, voice_tuning=VT(cutoff=v))
        cut[v] = round(res_peak(s.render(note(48, 0, 5), 4)[:, SR:].mean(axis=0)))
    out["vt_cutoff_hz"] = cut
    pan = {}
    for v in [0, 0.25, 0.75, 1]:
        s.load_params(BASE, voice_tuning=VT(pan=v))
        a = s.render(note(60, 0, 2), 1.5)
        pan[v] = {"left_db": round(rms_db(a[0]), 1), "right_db": round(rms_db(a[1]), 1)}
    out["vt_pan"] = pan
    env = {}
    for attr, base, what in [("attack", {"EnvAttackTime": 0.5}, "attack"), ("decay", {"EnvDecayTime": 0.5, "EnvSustainLevel": 0}, "decay"), ("release", {"EnvReleaseTime": 0.5}, "release")]:
        row = {}
        for v in [0, 0.5, 1]:
            s.load_params({**BASE, "NoDcOffset": 1, **base}, voice_tuning=VT(**{attr: v}))
            hold = 0.5 if what == "release" else 8
            r, dt = envelope(mono(s.render(note(48, 0, hold), 7)))
            if what == "attack":
                row[v] = round(float(np.argmax(r >= 0.9 * r.max()) * dt), 3)
            elif what == "decay":
                k = int(np.argmax(r))
                row[v] = round(float(np.argmax(r[k:] <= 0.1 * r[k]) * dt), 3)
            else:
                row[v] = round(float(np.argmax(r[int(0.5 / dt) :] <= 0.1 * r[int(0.3 / dt)]) * dt), 3)
        env[attr] = row
    out["vt_envelope_s"] = env
    # Round robin: repeated notes with each voice at its own pitch and pan.
    tunes = [{"detune": [0, 1, 0.2, 0.8][i % 4]} for i in range(12)]
    rr = {}
    for mode in [0, 1]:
        s.load_params({**TONE, "NumberOfVoices": 3, "RoundRobin": mode}, voice_tuning=tunes)
        midi = sum((note(60, i * 0.6, i * 0.6 + 0.45) for i in range(8)), [])
        x = mono(s.render(midi, 5))
        c, dt = pitch_track(x, C4, win=4096)
        rr[mode] = [round(float(np.median(c[int((i * 0.6 + 0.08) / dt) : int((i * 0.6 + 0.35) / dt)])), 1) for i in range(8)]
    out["round_robin_cents"] = rr
    return out


def arp():
    out = {"mode_panel": display("arpmode", "arp_mode", range(6)), "sync_panel": display("arpsyncmode", "arp_sync_mode", range(3)),
           "rate_panel_free": display("arprate", "arp_rate", UNIT)}
    for mode in [1, 2]:
        out[f"rate_panel_sync{mode}"] = display("arprate", "arp_rate", [round(i * 0.05, 2) for i in range(21)], arpsyncmode=mode)
    tones = np.array([48, 52, 55, 60, 64, 67, 72, 76, 79, 84, 88, 91, 96, 100, 103, 108])
    def seq(p, dur=8, start=0.0):
        s.load_params({"DcoWaveSaw": 0, "DcoWavePulse": 1, "NumberOfVoices": 5, "arpmode": 1, "arpsyncmode": 2, "arprate": 0.35,
                       "arprange": 0, "VcaEnvMode": 1, "VcfCutoff": 0.75, **p})
        midi = sum((note(n, start, dur + 1) for n in [60, 64, 67]), [])
        a = s.render(midi, dur).mean(axis=0)
        pitches = []
        for i in range(int(start * SR), len(a) - 2205, 220):
            f, m = spectrum(a[i : i + 2205])
            band = f > 100
            hz = f[band][int(np.argmax(m[band]))]
            pitches.append(int(tones[np.argmin(np.abs(tones - (69 + 12 * np.log2(hz / 440))))]))
        runs, starts = [pitches[0]], [0]
        for k, v in enumerate(pitches):
            if v != runs[-1]:
                runs.append(v)
                starts.append(k)
        return runs, np.array(starts) * 220 / SR
    out["mode_sequences"] = {m: seq({"arpmode": m})[0][:20] for m in range(1, 6)}
    out["range_sequences"] = {r: seq({"arprange": r})[0][:14] for r in range(4)}
    rates = {}
    for sync, values in [(0, [0.3, 0.4, 0.5, 0.6]), (1, [0.15, 0.35, 0.5, 0.65]), (2, [0.15, 0.35, 0.5, 0.65])]:
        for v in values:
            _, st = seq({"arpsyncmode": sync, "arprate": v})
            d = np.diff(st)
            rates[f"sync{sync}/{v}"] = {"panel": display("arprate", "arp_rate", [v], arpsyncmode=sync)[str(v)], "steps_per_s": round(float(1 / np.median(d)), 2) if len(d) else None}
    out["rates_at_120bpm"] = rates
    # Off-grid note: does the first step change wait for the beat grid, or count from the note?
    out["first_change_after_note_s"] = {sync: {start: round(float(seq({"arpsyncmode": sync, "arprate": 0.15}, start=start)[1][1]), 3) for start in [1.13, 1.37]} for sync in [1, 2]}
    return out


SECTIONS = {f.__name__: f for f in [lfo, performance, oscillator, filt, envelope_more, chorus, delay, reverb, eq, voices, arp]}

if __name__ == "__main__":
    data = json.load(open(PATH)) if os.path.exists(PATH) else {}
    for name in sys.argv[1:] or SECTIONS:
        data[name] = SECTIONS[name]()
        with open(PATH, "w") as f:
            json.dump(data, f, indent=1)
        print(name, "done", flush=True)
