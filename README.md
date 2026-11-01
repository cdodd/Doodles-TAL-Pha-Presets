# Doodles TAL-Pha Presets

Synthwave-style presets for [TAL-Pha](https://tal-software.com/products/tal-pha), an Alpha Juno II emulator synth by TAL Software, with notes that explain the
sound design.

## Installing

The steps are the same on Linux, macOS and Windows.

1. Download [Doodles-TAL-Pha-Presets.zip](https://github.com/cdodd/Doodles-TAL-Pha-Presets/releases/latest/download/Doodles-TAL-Pha-Presets.zip) and extract it.
2. In TAL-Pha, open the preset browser and click **Open Folder…**.
3. Copy the `Doodles` folder into the folder that opens.
4. In the preset browser, press **Reload** and filter by the `Doodles` bank.

If you've cloned this repo, skip step 1 and copy `presets/Doodles` instead.

## Docs

Read the full docs, with audio previews, at [cdodd.github.io/Doodles-TAL-Pha-Presets](https://cdodd.github.io/Doodles-TAL-Pha-Presets/), or open [docs/html/index.html](docs/html/index.html) in a browser.

## Rebuilding

Patches are defined in `patches/*.toml`. Needs Python 3.11 or later, TAL-Pha installed at `~/.vst3/TAL-Pha.vst3`, `ffmpeg`, and the Python packages in `requirements.txt`.

```bash
pip install -r requirements.txt
```

```bash
python3 tools/build.py
```

```bash
python3 tools/verify.py
```

```bash
python3 tools/make_recipes.py
```

```bash
python3 tools/make_docs.py
```

`build.py` writes the presets, setting each one's level. `verify.py` loads each through the plugin, measures it,
checks it against its stated profile, and renders previews. `make_recipes.py` renders each step of `recipes/*.toml`, checking that the sound does what the step says and that the last step matches the real preset. `make_docs.py` writes the HTML docs from all of that, plus the guide sources in `tools/guides/`.
`tools/make_gallery.py` renders the gallery and writes `tools/guides/gallery.md`, so change that page in the script rather than in the Markdown. `tools/calibrate.py` and `tools/calibrate_controls.py` re-measure the plugin's controls. `tools/verify.py --factory` also benchmarks the factory basses.

`tools/template.xml` is the plugin's init state, which every preset builds on. `plugin_state_xml` in `tools/talalpha.py` reads that state from a loaded plugin, if it ever needs replacing for a new plugin version.

## How it works

- **Presets are generated.** A `.talalpha` file is plain XML, so each one is built from `patches/*.toml`. Factory files are v7 or v8 and the current plugin writes v9, so new presets start from the plugin's own current state.
- **Every preset is proven to load.** TAL-Pha runs headlessly through `pedalboard`, so each file goes through the plugin's real state loader and is measured and rendered without opening a DAW.
- **The docs quote panel values.** The plugin reports its values in display units, such as an LFO rate of 0.95 Hz, rather than raw 0–1 numbers. `resonance_boost`, `portamento_mode`, `arp_range` and `number_of_voices` report unreliable text, so their real behaviour was measured by rendering.
- **Levels are comparable.** The bank targets -18 LUFS so auditioning is a fair comparison. Headroom wins over loudness, so short, punchy patches can sit several dB under it.

## Known limits

- **Measuring isn't listening.** The checks catch silence, clipping, wrong envelopes and bad tuning, not whether a patch sounds good. Near-duplicates within a category only raise a warning.
- **Tuning isn't checked everywhere.** Chord, arp and atonal patches (30 of the 100) can't be measured that way.
- **Rendering runs at a fixed 120 BPM.** The arp and synced delay work there, but tempo-synced patches haven't been checked at other tempos.
- **Funk Clav can fail `verify.py`.** Its phrase peak varies with oscillator phase, from about -4 to -0.4 dBFS, so it occasionally goes over the -1 dBFS limit. It hasn't clipped, so its Volume stays as it is and a failure on this patch alone can be ignored.
- **Some plugin behaviour is untested:** chord memory mono mode, whether U&D II differs from U&D on longer chords, and SYNC against SYNC HOST with a running transport.

## Licence

Released into the public domain under [CC0 1.0](LICENSE): use it for anything, with no attribution needed and no warranty.

This project isn't affiliated with or endorsed by TAL Software. TAL-Pha is their product, and CC0 grants no rights in their name or software.
