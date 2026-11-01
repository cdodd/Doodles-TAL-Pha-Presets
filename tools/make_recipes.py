"""Render each step of recipes/*.toml, measure it and check it against what the step claims.

Writes docs/data/recipes/<category>.json and step previews in audio/recipes/. Exits non-zero on failure.
"""
import glob
import json
import os
import sys
import tomllib
import xml.etree.ElementTree as ET

import numpy as np
from mido import Message
from scipy.signal import sosfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank
from talalpha import Synth, load_template, note
from verify import write_mp3

TOLERANCE = {"centroid_hz": 1.03, "lufs": 0.2, "sustain_db": 0.5, "sweep_octaves": 0.1, "vel_bright_ratio": 1.1,
             "mw_bright_ratio": 1.1, "attack_s": 0.005, "side_mid": 0.02, "tail_ms": 20, "short_tail_ms": 20, "mw_vibrato_cents": 3,
             "peak_db": 0.5, "low_energy_pct": 1.1, "at_bright_ratio": 1.1, "arp_notes_per_s": 0.5, "vibrato_cents": 3,
             "early_vibrato_cents": 3}
FINAL_MATCH_KEYS_IGNORED = {"path", "programname"}


def chord_notes(program):
    chord = program.find("Chord")
    return [n for n in (int(chord.get(f"midiNote{i}")) for i in range(6)) if n >= 0]


def load_recipes():
    recipes = []
    for path in sorted(glob.glob(os.path.join(bank.ROOT, "recipes", "*.toml"))):
        with open(path, "rb") as f:
            recipe = tomllib.load(f)
        recipe["slug"] = os.path.splitext(os.path.basename(path))[0]
        recipes.append(recipe)
    return recipes


def wheel_ramp(start, end, steps=64):
    return [Message("control_change", control=1, value=int(127 * i / steps),
                    time=start + (end - start) * i / steps) for i in range(steps + 1)]


def tail_ms(synth, pitch=45, hold=1.0):
    """Time after note-off for a note's level to fall 40 dB below its held level."""
    # High-passed: the DCO's DC offset otherwise reads as a long low-level tail.
    audio = sosfilt(bank._hp30, synth.render(note(pitch, 0, hold), hold + 0.6).mean(axis=0))
    win = 110
    n = len(audio) // win
    env = np.sqrt((audio[: n * win].reshape(n, win) ** 2).mean(axis=1))
    off = int(hold * bank.SR / win)
    held = env[max(off - 20, 0) : off].mean()
    below = np.where(env[off:] < held * 0.01)[0]
    return float(below[0] * win / bank.SR * 1000) if len(below) else 600.0


def measure(synth, recipe, wheel):
    midi, seconds = bank.phrase(recipe["phrase"], recipe.get("transpose", 0))
    if wheel:
        tail = max(m.time for m in midi)
        midi = sorted(midi + wheel_ramp(tail / 2, tail), key=lambda m: m.time)
    audio = synth.render(midi, seconds)
    m = bank.measure_phrase(audio)
    pitch, hold = bank.test_setup(recipe["category"], recipe)
    m.update(bank.measure_note(synth.render(note(pitch, 0, hold), hold + 0.5), 440 * 2 ** ((pitch - 69) / 12), hold))
    m.update(bank.measure_response(
        lambda v: synth.render(note(pitch, 0, 1.5, v), 1.5),
        lambda cc: synth.render([Message("control_change", control=1, value=cc, time=0)] + note(pitch, 0.01, 2), 2),
        repeats=2,
        render_touch=lambda at: synth.render([Message("aftertouch", value=at, time=0.02)] + note(pitch, 0.01, 2), 2)))
    m["tail_ms"] = tail_ms(synth, pitch)
    m["short_tail_ms"] = tail_ms(synth, pitch, 0.08)
    m["arp_notes_per_s"] = bank.notes_per_second(audio)
    held = synth.render(note(pitch, 0, 2.5), 2.5)
    m["vibrato_cents"] = bank.pitch_spread(held[:, int(1.0 * bank.SR) :])
    m["early_vibrato_cents"] = bank.pitch_spread(held[:, : int(0.4 * bank.SR)])
    return m, audio


def moved(key, before, after, direction):
    tol = TOLERANCE[key]
    if key in ("centroid_hz", "vel_bright_ratio", "mw_bright_ratio", "at_bright_ratio", "low_energy_pct"):
        return after > before * tol if direction == "up" else after < before / tol
    return after > before + tol if direction == "up" else after < before - tol


def main():
    only = sys.argv[1:]
    synth = Synth(bank.SR)
    data_dir = os.path.join(bank.ROOT, "docs", "data", "recipes")
    os.makedirs(data_dir, exist_ok=True)
    template_program = load_template().find("programs/program")
    template = template_program.attrib
    failures = []
    for recipe in load_recipes():
        if only and recipe["slug"] not in only:
            continue
        preset_file = bank.preset_path(recipe["category"], recipe["patch"])
        target_program = ET.parse(preset_file).getroot().find("programs/program")
        target = target_program.attrib
        params, steps, previous, chord = {}, [], None, None
        for i, step in enumerate(recipe["step"]):
            changes = dict(step.get("set", {}))
            if step.get("set_volume_from_preset"):
                changes["Volume"] = float(target["Volume"])
            before = {k: float(params.get(k, template[k])) for k in changes}
            params.update(changes)
            chord = step.get("chord", chord)
            synth.load_params(params, chord=chord)
            m, audio = measure(synth, recipe, step.get("wheel", False))
            if np.abs(audio).max() >= 1:
                failures.append(f"step {i + 1}: clips")
            for key, direction in step.get("expect", {}).items():
                if previous and not moved(key, previous[key], m[key], direction):
                    failures.append(f"step {i + 1} '{step['title']}': {key} should go {direction}, "
                                    f"{previous[key]:.2f} -> {m[key]:.2f}")
            rel = os.path.join("audio", "recipes", recipe["slug"], f"step-{i + 1:02}.mp3")
            write_mp3(audio, os.path.join(bank.ROOT, rel))
            shown = list(step.get("expect", {})) + step.get("show", [])
            measures = {k: [previous[k] if previous else None, m[k]] for k in shown}
            steps.append({"audio": rel, "before": before, "after": changes, "measures": measures})
            previous = m
            print(f"{i + 1:2} {step['title'][:42]:42} {m['lufs']:6.1f} LUFS atk {m['attack_s'] * 1000:4.0f} L/R {m['side_mid']:.2f} pk {m['peak_db']:5.1f} "
                  f"cent {m['centroid_hz']:6.0f}  sweep {m['sweep_octaves']:5.2f}  sus {m['sustain_db']:6.1f}  "
                  f"vel {m['vel_bright_ratio']:5.2f}x  mw {m['mw_bright_ratio']:5.2f}x  tail {m['tail_ms']:4.0f} ms")
        # The last step must be the real preset: compare every parameter with the file.
        for key, value in target.items():
            if key in FINAL_MATCH_KEYS_IGNORED:
                continue
            expected = float(params.get(key, template[key]))
            if abs(float(value) - expected) > 1e-6:
                failures.append(f"final step differs from preset: {key} recipe {expected} preset {value}")
        final_chord = chord if chord is not None else chord_notes(template_program)
        if final_chord != chord_notes(target_program):
            failures.append(f"final step differs from preset: chord recipe {final_chord} preset {chord_notes(target_program)}")
        with open(os.path.join(data_dir, recipe["slug"] + ".json"), "w") as f:
            json.dump({"steps": steps}, f, indent=1)
    for failure in failures:
        print("FAIL", failure)
    print(f"{len(failures)} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
