"""Build presets from patches/*.toml, normalising each to the category's loudness target."""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank
from talalpha import Synth, build_preset, load_xml_into_plugin

GAIN_DB_PER_VOLUME_DOUBLING = 12.0  # measured in tools/calibrate.py


def build(synth, cat, patch):
    name, category = patch["name"], cat["category"]
    midi, seconds = bank.phrase(patch["phrase"], patch.get("transpose", 0))
    target = patch.get("lufs", bank.TARGET_LUFS)
    params = dict(patch["params"], Volume=0.5)
    make = lambda: build_preset(
        synth.template, name, params, bank=bank.BANK, category=category, author=bank.AUTHOR,
        description=patch["browser"], tags=[category] + [x.title() for x in patch["tags"]], chord=patch.get("chord"))
    for _ in range(5):
        load_xml_into_plugin(synth.plugin, make())
        # Averaged because free-running unison and chorus vary between renders.
        audio = [synth.render(midi, seconds) for _ in range(3)]
        level = sum(bank.lufs(a) for a in audio) / 3
        peak = max(float(20 * np.log10(np.abs(a).max() + 1e-9)) for a in audio)
        # Headroom wins over loudness: sparse, punchy sounds can't reach the target without clipping.
        change_db = min(target - level, bank.PEAK_LIMIT_DB - peak)
        if abs(change_db) < 0.2 or (change_db > 0 and params["Volume"] >= 1.0):
            break
        params["Volume"] = min(1.0, params["Volume"] * 2 ** (change_db / GAIN_DB_PER_VOLUME_DOUBLING))
    path = bank.preset_path(category, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(make())
    print(f"{name:20} Volume {params['Volume']:.3f}  {level:6.1f} LUFS  peak {peak:5.1f}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category")
    parser.add_argument("names", nargs="*")
    args = parser.parse_args()
    synth = Synth(bank.SR)
    for cat in bank.load_categories():
        if args.category and cat["slug"] != args.category:
            continue
        for patch in cat["patch"]:
            if not args.names or patch["name"] in args.names:
                build(synth, cat, patch)


if __name__ == "__main__":
    main()
