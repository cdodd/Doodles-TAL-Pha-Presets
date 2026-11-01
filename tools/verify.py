"""Load every built preset through the plugin, render and measure it, and check its stated profile.

Writes docs/data/measurements/<category>.json and renders preview MP3s. Exits non-zero on failure.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
import wave
import xml.etree.ElementTree as ET

import numpy as np
from mido import Message

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank
from talalpha import Synth, note

DUPLICATE_DISTANCE = 2.0  # dB, mean across bands and time
MONO_LOSS_LIMIT_DB = -3.0
TUNING_LIMIT_CENTS = 15
SHORT_NOTE_TUNING_LIMIT_CENTS = 60
LOUDNESS_TOLERANCE_DB = 1.5  # free-running unison and chorus vary between renders


def write_mp3(audio, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(bank.SR)
            w.writeframes((np.clip(audio.T, -1, 1) * 32767).astype(np.int16).tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp.name, "-q:a", "3", path], check=True)


def measure_file(synth, path, phrase_name, category="Bass", patch=None, repeats=10):
    synth.load_file(path)
    patch = patch or {}
    midi, seconds = bank.phrase(phrase_name, patch.get("transpose", 0))
    audio = synth.render(midi, seconds)
    result = bank.measure_phrase(audio)
    result["arp_notes_per_s"] = bank.notes_per_second(audio)
    pitch, hold = bank.test_setup(category, patch)
    # Median of three: free-running unison can beat to a late peak, which moves the half-level point in a single render.
    notes = [bank.measure_note(synth.render(note(pitch, 0, hold), hold + 0.5), 440 * 2 ** ((pitch - 69) / 12), hold)
             for _ in range(3)]
    result.update(sorted(notes, key=lambda n: n["attack_s"])[1])
    result.update(bank.measure_response(
        lambda v: synth.render(note(pitch, 0, 1.5, v), 1.5),
        lambda cc: synth.render([Message("control_change", control=1, value=cc, time=0)] + note(pitch, 0.01, 2), 2),
        repeats,
        lambda at: synth.render([Message("aftertouch", value=at, time=0.02)] + note(pitch, 0.01, 2), 2)))
    return result, audio


def check_loaded(synth, path):
    """The plugin must report the same values the file holds."""
    program = ET.parse(path).getroot().find("programs/program").attrib
    params = synth.plugin.parameters
    errors = []
    for attr, key in [("VcfCutoff", "vcf_cutoff"), ("VcfResonance", "vcf_resonance"), ("EnvDecayTime", "decay_time")]:
        if abs(float(program[attr]) - params[key].raw_value) > 1e-3:
            errors.append(f"{attr} file={program[attr]} plugin={params[key].raw_value}")
    return errors


def check_patch(patch, category, m, known, fail):
    target = patch.get("lufs", bank.TARGET_LUFS)
    if m["lufs"] < -60:
        fail("silent")
    if m["peak_db"] > -1:
        fail(f"too hot, peak {m['peak_db']:.1f} dBFS")
    # Quieter than the target is fine when the peak is what limited it.
    if abs(m["lufs"] - target) > LOUDNESS_TOLERANCE_DB and m["peak_db"] < bank.PEAK_LIMIT_DB - 3:
        fail(f"loudness {m['lufs']:.1f} LUFS")
    # Arps and chords sound several pitches at once, so one note's harmonic series doesn't apply.
    tonal = not (patch.get("atonal") or patch.get("chord") or patch["params"].get("arpmode"))
    # A very short note can't be measured as finely.
    if tonal and abs(m["cents_off"]) > (SHORT_NOTE_TUNING_LIMIT_CENTS if m["short_note"] else TUNING_LIMIT_CENTS):
        fail(f"out of tune by {m['cents_off']:.0f} cents, strongest partial {m['strongest_hz']:.1f} Hz")
    if m["mono_loss_db"] < MONO_LOSS_LIMIT_DB:
        fail(f"loses {-m['mono_loss_db']:.1f} dB when summed to mono")
    claims = patch["browser"]
    if "Vel: none" in claims and (m["vel_bright_ratio"] > 1.15 or
                                  abs(m["vel_level_db"]) > max(1, 3 * m["vel_level_noise"])):
        fail(f"claims no velocity response: {m['vel_bright_ratio']:.2f}x, {m['vel_level_db']:.1f} dB")
    if "Vel: brightness" in claims and m["vel_bright_ratio"] < 1.3:
        fail(f"claims velocity brightness: {m['vel_bright_ratio']:.2f}x")
    if ("+ level" in claims or "Vel: level" in claims) and m["vel_level_db"] < 3:
        fail(f"claims velocity level: {m['vel_level_db']:.1f} dB")
    if "MW: open filter" in claims and m["mw_bright_ratio"] < 1.15:
        fail(f"claims mod wheel opens filter: {m['mw_bright_ratio']:.2f}x")
    if "MW: none" in claims and abs(m["mw_bright_ratio"] - 1) > 0.1:
        fail(f"claims no mod wheel: {m['mw_bright_ratio']:.2f}x")
    if "MW: vibrato" in claims and m["mw_vibrato_cents"] < 5:
        fail(f"claims mod wheel vibrato: {m['mw_vibrato_cents']:.0f} cents")
    if "AT: open filter" in claims and m["at_bright_ratio"] < 1.15:
        fail(f"claims aftertouch opens filter: {m['at_bright_ratio']:.2f}x")
    if patch["params"].get("arpmode", 0) and m["arp_notes_per_s"] < 1.5:
        fail(f"arp isn't running: {m['arp_notes_per_s']:.1f} notes per second")
    for key, spec in patch.get("expect", {}).items():
        if key == "low_side_mid_max":
            if m["low_side_mid"] > spec:
                fail(f"low-end width {m['low_side_mid']:.2f} > {spec}")
        elif not spec[0] <= m[key] <= spec[1]:
            fail(f"{key} {m[key]:.3f} outside {spec}")
    for pairing in patch["pairings"]:
        if not pairing.get("external") and pairing["with"] not in known:
            fail(f"pairing '{pairing['with']}' is not in the roster")
    unused = [k for k in patch["why"] if k not in patch["params"]]
    if unused:
        fail(f"why names unset params {unused}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category")
    parser.add_argument("--factory", action="store_true")
    args = parser.parse_args()
    synth = Synth(bank.SR)
    known = {n for names in bank.load_roster().values() for n in names}
    data_dir = os.path.join(bank.ROOT, "docs", "data", "measurements")
    os.makedirs(data_dir, exist_ok=True)
    failures, warnings, count = [], [], 0
    for cat in bank.load_categories():
        if args.category and cat["slug"] != args.category:
            continue
        results = {}
        fingerprints = {}
        compare = bank.COMPARE_PHRASE[cat["category"]]
        for patch in cat["patch"]:
            name = patch["name"]
            path = bank.preset_path(cat["category"], name)
            # Free-running unison and PWM need more renders for a stable average.
            params = patch["params"]
            repeats = 16 if params.get("UnisonoVoices", 0) or params.get("DcoPwmDepth", 0) else 4
            m, audio = measure_file(synth, path, patch["phrase"], cat["category"], patch, repeats)
            fail = lambda msg, name=name: failures.append(f"{name}: {msg}")
            for e in check_loaded(synth, path):
                fail("load mismatch " + e)
            check_patch(patch, cat["category"], m, known, fail)
            # Same phrase for every patch in a category, so the comparison is about the sound, not the notes.
            fingerprints[name] = bank.fingerprint(synth.render(*bank.phrase(compare)))
            results[name] = m
            write_mp3(audio, os.path.join(bank.ROOT, bank.audio_rel(cat["slug"], name)))
            print(f"{name:18} {m['lufs']:6.1f} LUFS  pk {m['peak_db']:5.1f}  cent {m['centroid_hz']:6.0f} Hz  "
                  f"low {m['low_energy_pct']:3.0f}%  L/R {m['side_mid']:.2f}/{m['low_side_mid']:.2f}  "
                  f"atk {m['attack_s'] * 1000:4.0f} ms  sweep {m['sweep_octaves']:5.2f} oct  "
                  f"sus {m['sustain_db']:6.1f} dB  {m['strongest_hz']:6.1f} Hz {m['cents_off']:+.0f}c  "
                  f"mono {m['mono_loss_db']:+.1f} dB  vel {m['vel_bright_ratio']:.2f}x/{m['vel_level_db']:+.1f} dB  "
                  f"mw {m['mw_bright_ratio']:.2f}x/{m['mw_vibrato_cents']:+.0f}c  at {m['at_bright_ratio']:.2f}x", flush=True)
        names = list(fingerprints)
        pairs = sorted((float(np.abs(fingerprints[a] - fingerprints[b]).mean()), a, b)
                       for i, a in enumerate(names) for b in names[i + 1 :])
        print("closest pairs:", [(round(d, 1), a, b) for d, a, b in pairs[:3]])
        with open(os.path.join(data_dir, cat["slug"] + ".json"), "w") as f:
            json.dump(results, f, indent=1)
        count += len(results)
        for d, a, b in pairs:
            if d < DUPLICATE_DISTANCE:
                warnings.append(f"near-duplicate spectrum: {a} / {b} ({d:.1f} dB)")
    if not args.category:
        names = {p["name"]: c["category"] for c in bank.load_categories() for p in c["patch"]}
        names_seen = [n for names_ in bank.load_roster().values() for n in names_]
        if sorted(names) != sorted(names_seen):
            failures.append(f"roster mismatch: {sorted(set(names) ^ set(names_seen))}")
    if args.factory:
        benchmark(synth)
    for w in warnings:
        print("WARNING", w)
    for f in failures:
        print("FAIL", f)
    print(f"{count} presets, {len(failures)} failures, {len(warnings)} warnings")
    sys.exit(1 if failures else 0)


def benchmark(synth):
    """Same measurements on factory basses, as a reference for what a usable bass looks like."""
    rows = []
    root = os.path.expanduser("~/.toguaudioline/TAL-Pha/presets")
    for path in glob.glob(root + "/**/*.talalpha", recursive=True):
        r = ET.parse(path).getroot()
        if "bass" not in r.get("tags", "").lower() and "/Bass/" not in path:
            continue
        m, _ = measure_file(synth, path, "rolling")
        rows.append(m)
    print(f"factory basses (n={len(rows)}):")
    for key in ["lufs", "peak_db", "centroid_hz", "low_energy_pct", "side_mid", "low_side_mid", "attack_s", "sweep_octaves"]:
        v = np.array([r[key] for r in rows])
        print(f"  {key:16} p10 {np.percentile(v, 10):8.2f}  p50 {np.percentile(v, 50):8.2f}  p90 {np.percentile(v, 90):8.2f}")


if __name__ == "__main__":
    main()
