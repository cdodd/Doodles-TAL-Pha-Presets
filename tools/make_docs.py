"""Generate the HTML docs from patch data, guide sources, built presets and measurements."""
import glob
import json
import tomllib
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank
import make_recipes
import site_html as site
from talalpha import load_plugin

HERE = os.path.dirname(os.path.abspath(__file__))
CAL = json.load(open(os.path.join(bank.ROOT, "docs", "data", "calibration.json")))
MEAS = {}
for path in glob.glob(os.path.join(bank.ROOT, "docs", "data", "measurements", "*.json")):
    with open(path) as f:
        MEAS.update(json.load(f))
plugin = load_plugin()


def interp(table, value, inner=None):
    xs = sorted(float(k) for k in table)
    ys = [table[str(x) if str(x) in table else str(int(x))] for x in xs]
    if inner:
        ys = [y[inner] for y in ys]
    return float(np.exp(np.interp(value, xs, np.log(np.maximum(ys, 1e-3)))))


def seconds(v, which):
    t = interp(CAL["envelope_seconds"], v, which)
    return f"{t * 1000:.0f} ms" if t < 1 else f"{t:.1f} s"


def via_plugin(key, raw, **context):
    # Some displays depend on another control, such as a sync switch.
    for other, value in context.items():
        plugin.parameters[other].raw_value = value
    p = plugin.parameters[key]
    p.raw_value = raw
    return str(p.string_value)


def scale(v):
    return f"{v * 10:.1f}"


SAW = ["Off", "Saw", "Saw 2", "Saw PW", "Saw 3", "Saw 4"]
PULSE = ["Off", "Square", "Pulse 25%", "Pulse PW", "Saw (TAL addition)"]
SUB = ["Square -1 oct (panel label: OFF)", "Pulse 25% -1 oct", "Mixed -1 oct", "Bright square -1 oct", "Square -2 oct",
       "Pulse 25% -2 oct"]
ENVF = ["Normal", "Inverted", "Normal-Dynamic", "Dynamic"]
VCA = ["Normal", "Gate", "Normal-Dynamic", "Gate-Dynamic"]
HPF = ["Bass boost", "Off", "HP 1", "HP 2"]
LFO = ["Triangle", "Sine", "Saw", "REC", "S&H", "Noise"]

PANEL = {
    "DcoRange": ("DCO Range", lambda v: ["4'", "8'", "16'", "32'"][int(v)]),
    "DcoWaveSaw": ("DCO Saw", lambda v: SAW[int(v)]),
    "DcoWavePulse": ("DCO Pulse", lambda v: PULSE[int(v)]),
    "DcoWaveSub": ("Sub wave", lambda v: SUB[int(v)]),
    "DcoSubLevel": ("Sub level", lambda v: f"{v:.1f} / 3"),
    "DcoPwmDepth": ("PWM", scale),
    "DcoPwmRate": ("PWM Rate", scale),
    "specialPulseSync": ("Pulse Sync", lambda v: "On" if v else "Off"),
    "specialPulseTune": ("Pulse Tune", lambda v: f"{v:+.0f} st"),
    "specialPulseFineTune": ("Pulse Fine", lambda v: f"{v * 100:+.0f} cents"),
    "specialPulseVolume": ("Pulse Volume", scale),
    "specialPulseDcoEnv": ("Pulse Env mod", lambda v: f"{v:+.2f}"),
    "HpfCutoff": ("HPF", lambda v: HPF[int(v)]),
    "resonanceBoostFrequency": ("Bass boost ALT", lambda v: "On (+6 dB at 80 Hz)" if v else "Off"),
    "VcfCutoff": ("VCF Cutoff", lambda v: f"{scale(v)} (about {interp(CAL['cutoff_hz'], v):.0f} Hz at C4)"),
    "VcfResonance": ("VCF Res", scale),
    "VcfEnvMode": ("VCF Env mode", lambda v: ENVF[int(v)]),
    "VcfEnvMod": ("VCF Env", scale),
    "VcfKeyFollow": ("VCF Key follow", scale),
    "VcfLfoMod": ("VCF LFO", scale),
    "VcaEnvMode": ("VCA mode", lambda v: VCA[int(v)]),
    "EnvAttackTime": ("Env T1 (attack)", lambda v: f"{scale(v)} (about {seconds(v, 'attack_to_90pct')})"),
    "EnvDecayTime": ("Env T3 (decay)", lambda v: f"{scale(v)} (about {seconds(v, 'decay_to_-20dB')} to -20 dB)"),
    "EnvSustainLevel": ("Env L3 (sustain)", scale),
    "EnvReleaseTime": ("Env T4 (release)", lambda v: f"{scale(v)} (about {seconds(v, 'release_to_-20dB')} to -20 dB)"),
    "EnvKeyFollow": ("Env Key follow", scale),
    "NumberOfVoices": ("Voices", lambda v: "Mono (1)" if v == 0 else f"{int(v) + 1}"),
    "PortamentoMode": ("Portamento", lambda v: ["Off", "On (overlapping notes)", "All notes"][int(v)]),
    "PortamentoTime": ("Portamento Time", scale),
    "BenderRange": ("Bend range", lambda v: f"{v:.0f} st"),
    "UnisonoVoices": ("Unison voices", lambda v: via_plugin("unison_voices", v)),
    "UnisonoDetune": ("Unison detune", lambda v: f"{v:.2f}"),
    "UnisonoSpread": ("Unison spread", lambda v: f"{v:.2f}"),
    "DcoChorusSwitch": ("Chorus", lambda v: "On" if v else "Off"),
    "ChorusRate": ("Chorus Rate", scale),
    "LfoWaveform": ("LFO wave", lambda v: LFO[int(v)]),
    "LfoRate": ("LFO Rate", lambda v: via_plugin("lfo_rate", v)),
    "eqBellFreq": ("EQ Freq", lambda v: via_plugin("eq_freq", v)),
    "eqBellQ": ("EQ Q", lambda v: via_plugin("eq_q", v)),
    "eqBellGain": ("EQ Gain", lambda v: f"{v:+.1f} dB"),
    "ModWheelVcfRange": ("MW to VCF", scale),
}
onoff = lambda v: "On" if v else "Off"
bipolar = lambda v: f"{(v - 0.5) * 10:+.2f}"  # Tone and spread read -5 to +5, with 0.5 in the file at the centre.
ENVD = ["Normal", "Inverted", "Normal-Dynamic", "Inverted-Dynamic"]
ARP_MODES = ["Off", "Up", "Down", "Up & down", "Random", "Up & down II"]
ARP_SYNC = ["No sync", "Sync", "Host sync"]
PANEL.update({
    "ModWheelDcoLfo": ("MW to DCO LFO", scale),
    "ModWheelVcfLfo": ("MW to VCF LFO", scale),
    "Volume": ("Volume", scale),
    "Noise": ("Noise", lambda v: f"{v:.1f} / 3"),
    "DcoEnvMode": ("DCO Env mode", lambda v: ENVD[int(v)]),
    "DcoEnvMod": ("DCO Env", lambda v: f"{scale(v)} (reads {via_plugin('dco_env_mod', v)})"),
    "DcoLfoMod": ("DCO LFO", scale),
    "DcoAtMod": ("DCO AT", scale),
    "VcfAftertouch": ("VCF AT", scale),
    "VcaAftertouch": ("VCA AT", scale),
    "VcaLevel": ("VCA Level", scale),
    "EnvAttackLevel": ("Env L1", scale),
    "EnvBreakTime": ("Env T2", scale),
    "EnvBreakLevel": ("Env L2", scale),
    "resonanceBoost": ("Res BOOST", onoff),
    "specialSawVolume": ("Saw Volume", scale),
    "specialPulseDcoLfo": ("Pulse LFO mod", lambda v: f"{v:+.2f}"),
    "RoundRobin": ("Round robin", onoff),
    "Octave": ("Octave", lambda v: f"{v:+.0f}"),
    "NoDcOffset": ("Clean DCO", onoff),
    "LfoDelay": ("LFO Delay", lambda v: via_plugin("lfo_delay", v)),
    "LfoSync": ("LFO Sync", onoff),
    "LfoTrigger": ("LFO Trig", onoff),
    "LfoInvert": ("LFO Inv", onoff),
    "reverbDryWet": ("Reverb mix", lambda v: via_plugin("fx_reverb_dry_wet", v)),
    "reverbSize": ("Reverb size", scale),
    "reverbDelay": ("Reverb pre-delay", lambda v: via_plugin("fx_reverb_delay", v)),
    "reverbTone": ("Reverb tone", bipolar),
    "delayDryWet": ("Delay mix", lambda v: via_plugin("fx_delay_dry_wet", v)),
    "delaySync": ("Delay Sync", onoff),
    "delaySpread": ("Delay spread", bipolar),
    "delayTone": ("Delay tone", bipolar),
    "delayFeedback": ("Delay feedback", scale),
    "arpmode": ("Arp mode", lambda v: ARP_MODES[int(v)]),
    "arprange": ("Arp range", lambda v: f"{int(v) + 1} oct"),
    "arpsyncmode": ("Arp sync", lambda v: ARP_SYNC[int(v)]),
})
NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def note_name(pitch):
    return f"{NOTE_NAMES[pitch % 12]}{pitch // 12 - 1}"


def hidden(key, value):
    # The init value isn't zero, so zero is set throughout. It's only worth showing when used.
    return key == "ModWheelDcoLfo" and value == 0


def param_cell(key, value, params=None):
    params = params or {}
    if key == "LfoRate":
        return "LFO Rate", via_plugin("lfo_rate", value, lfo_sync=params.get("LfoSync", 0))
    if key == "delayTime":
        return "Delay Time", via_plugin("fx_delay_time", value, fx_delay_sync=params.get("delaySync", 1))
    if key == "arprate":
        return "Arp Rate", via_plugin("arp_rate", value, arp_sync_mode=params.get("arpsyncmode", 0) / 2)
    label, fmt = PANEL[key]
    return label, fmt(value)


def patch_params(cat, patch):
    """Returns (significant rows of (label, value, why), other rows of (label, value))."""
    root = ET.parse(bank.preset_path(cat["category"], patch["name"])).getroot()
    params = {k: float(v) for k, v in root.find("programs/program").attrib.items() if k in patch["params"]}
    significant = [(*param_cell(key, params[key], params), why) for key, why in patch["why"].items()]
    if "chord" in patch:
        chord = " ".join(note_name(n) for n in patch["chord"])
        significant.insert(0, ("Chord memory", chord, patch["chord_why"]))
    other = [param_cell(k, v, params) for k, v in params.items() if k not in patch["why"] and not hidden(k, v)]
    return significant, other


METRICS = {
    "centroid_hz": ("Brightness", lambda v: f"{v:,.0f} Hz"),
    "lufs": ("Loudness", lambda v: f"{v:.1f} LUFS"),
    "sustain_db": ("Held level", lambda v: f"{v:.0f} dB from peak"),
    "sweep_octaves": ("Filter sweep", lambda v: f"{max(v, 0):.1f} octaves"),
    "vel_bright_ratio": ("Hard note vs soft note brightness", lambda v: f"{v:.1f}x"),
    "mw_bright_ratio": ("Wheel up vs wheel down brightness", lambda v: f"{v:.1f}x"),
    "tail_ms": ("Tail after note-off", lambda v: f"{v:.0f} ms"),
    "short_tail_ms": ("Tail after a very short note", lambda v: f"{v:.0f} ms"),
    "attack_s": ("Time to half level", lambda v: f"{v * 1000:.0f} ms"),
    "side_mid": ("Stereo width (side/mid)", lambda v: f"{v:.2f}"),
    "mw_vibrato_cents": ("Vibrato with wheel up", lambda v: f"{max(v, 0):.0f} cents"),
    "at_bright_ratio": ("Aftertouch up vs off brightness", lambda v: f"{v:.1f}x"),
    "low_energy_pct": ("Energy below 150 Hz", lambda v: f"{v:.0f}%"),
    "peak_db": ("Peak", lambda v: f"{v:.1f} dBFS"),
    "arp_notes_per_s": ("Note rate", lambda v: f"{v:.1f} per second"),
    "vibrato_cents": ("Pitch movement on a held note", lambda v: f"{v:.0f} cents"),
    "early_vibrato_cents": ("Pitch movement in the first 400 ms", lambda v: f"{v:.0f} cents"),
}


def recipe_views():
    """Recipes with control changes and measurements formatted for display."""
    views = []
    for recipe in make_recipes.load_recipes():
        view = dict(recipe, steps=[])
        context = {}
        with open(os.path.join(bank.ROOT, "docs", "data", "recipes", recipe["slug"] + ".json")) as f:
            data = json.load(f)
        for step, result in zip(recipe["step"], data["steps"]):
            changes = []
            context.update(result["after"])
            for key, value in result["after"].items():
                label, before = param_cell(key, result["before"][key], context)
                changes.append((label, before, param_cell(key, value, context)[1]))
            if "chord" in step:
                changes.append(("Chord memory", "None", " ".join(note_name(n) for n in step["chord"])))
            measures = []
            for key, (before, after) in result["measures"].items():
                label, fmt = METRICS[key]
                measures.append((label, fmt(before), fmt(after)))
            view["steps"].append(dict(step, changes=changes, measures=measures, audio=result["audio"]))
        views.append(view)
    return views


def patch_slug(name, cats):
    for cat in cats:
        if any(p["name"] == name for p in cat["patch"]):
            return cat["slug"]
    raise KeyError(f"not in the bank: {name}")


def kits_markdown(cats):
    with open(os.path.join(HERE, "guides", "kits.toml"), "rb") as f:
        kits = tomllib.load(f)["kit"]
    lines = ["# Starter kits", "", "Five sets of patches that work as a track, each with a tempo, a chord progression "
             "and an arrangement to start from. Change anything you like.", ""]
    for kit in kits:
        lines += [f"## {kit['name']}", "", f"**{kit['genre']}** · {kit['tempo']} · {kit['key']}", "", kit["idea"], "",
                  "| Patch | Role |", "|---|---|"]
        for part in kit["parts"]:
            anchor = part["patch"].lower().replace(" ", "-")
            lines.append(f"| [{part['patch']}]({patch_slug(part['patch'], cats)}.html#{anchor}) | {part['role']} |")
        lines += ["", "**Arrangement**", ""] + [f"- {x}" for x in kit["arrangement"]]
        lines += ["", "**Mix:** " + kit["mix"], ""]
    return lines


def typical_values(cats):
    rows = [("Voices", "NumberOfVoices", lambda v: f"{v + 1:.0f}"), ("T1 attack", "EnvAttackTime", scale),
            ("T3 decay", "EnvDecayTime", scale), ("L3 sustain", "EnvSustainLevel", scale),
            ("T4 release", "EnvReleaseTime", scale), ("Cutoff", "VcfCutoff", scale), ("Res", "VcfResonance", scale),
            ("Filter env", "VcfEnvMod", scale), ("Key follow", "VcfKeyFollow", scale)]
    head = "| Category | " + " | ".join(r[0] for r in rows) + " | VCA Gate | Chorus | Unison |"
    lines = [head, "|" + "---|" * (len(rows) + 4)]
    for cat in cats:
        programs = [ET.parse(bank.preset_path(cat["category"], p["name"])).getroot().find("programs/program").attrib
                    for p in cat["patch"]]
        cells = [fmt(float(np.median([float(x[key]) for x in programs]))) for _, key, fmt in rows]
        count = lambda test: sum(1 for x in programs if test(x))
        cells += [f"{count(lambda x: float(x['VcaEnvMode']) in (1, 3))} of 10",
                  f"{count(lambda x: float(x['DcoChorusSwitch']))} of 10",
                  f"{count(lambda x: float(x['UnisonoVoices']))} of 10"]
        lines.append(f"| {cat['category']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def map_table(cats):
    lines = ["| Patch | Category | Brightness | Width (side/mid) | Below 150 Hz |", "|---|---|---|---|---|"]
    for cat in cats:
        for p in cat["patch"]:
            m = MEAS[p["name"]]
            lines.append(f"| {p['name']} | {cat['category']} | {m['centroid_hz']:,.0f} Hz | {m['side_mid']:.2f} | "
                         f"{m['low_energy_pct']:.0f}% |")
    return "\n".join(lines)


def main():
    cats = bank.load_categories()
    guides = {"kits": "\n".join(kits_markdown(cats))}
    for slug in ["control-reference", "gallery", "reaper-cheat-sheet"]:
        with open(os.path.join(HERE, "guides", slug + ".md")) as f:
            guides[slug] = f.read()
    with open(os.path.join(HERE, "guides", "field-guide.md")) as f:
        guides["field-guide"] = f.read().replace("{{typical_values}}", typical_values(cats))
    site.write_site(cats, MEAS, patch_params, recipe_views(), guides, map_table(cats))


if __name__ == "__main__":
    main()
