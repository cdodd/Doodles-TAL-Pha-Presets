"""Render a sample and spectrogram of each waveform and key control, for the gallery page."""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank
from talalpha import Synth, note
from verify import write_mp3

MONO = {"NumberOfVoices": 0, "Volume": 0.4, "ModWheelDcoLfo": 0}
SWEEP = dict(MONO, VcfCutoff=0.3, VcfEnvMod=0.55, EnvDecayTime=0.55, EnvSustainLevel=0, VcaEnvMode=1)
OPEN_PULSE = dict(MONO, DcoWaveSaw=0, DcoPwmRate=0.5, DcoPwmDepth=0.7)
# Transparent to one hue, with mid-grey axes, so the images work on light and dark pages.
CMAP = LinearSegmentedColormap.from_list("hue", [(0.48, 0.17, 0.88, 0), (0.48, 0.17, 0.88, 1)])

GROUPS = [
    ("Saw waveforms", "The manual shows these as icons. All are the same note, with the filter open.", [
        ("Saw", dict(MONO), "The full harmonic series, and the usual starting point."),
        ("Saw 2", dict(MONO, DcoWaveSaw=2), "The 2nd harmonic is strongest, so it sounds an octave up and hollow."),
        ("Saw PW", dict(MONO, DcoWaveSaw=3, DcoPwmDepth=0.7, DcoPwmRate=0.5), "Shifts continuously with PWM. Blacktop uses it."),
        ("Saw 3", dict(MONO, DcoWaveSaw=4), "Top-heavy and buzzy, with the 8th harmonic strongest."),
        ("Saw 4", dict(MONO, DcoWaveSaw=5), "Strong peaks at the 2nd, 6th and 8th harmonics: bell-like. Glass Chime uses it."),
    ]),
    ("Pulse waveforms", "Pulse positions can be retuned and synced separately from the saw.", [
        ("Square", dict(OPEN_PULSE, DcoWavePulse=1), "Odd harmonics only: hollow."),
        ("Pulse 25%", dict(OPEN_PULSE, DcoWavePulse=2), "Nasal, with every 4th harmonic missing."),
        ("Pulse PW", dict(OPEN_PULSE, DcoWavePulse=3), "The width moves, so the harmonics do too. This is the classic pad motion."),
        ("Saw position", dict(OPEN_PULSE, DcoWavePulse=4), "The plain saw's harmonic series, but it can be retuned and synced separately."),
    ]),
    ("Sub oscillator", "Alone at full level, played at A3. Only level 0 turns the sub off.", [
        ("Square -1 oct", dict(MONO, DcoWaveSaw=0, DcoWaveSub=0, DcoSubLevel=3), "The panel labels this position OFF."),
        ("Pulse 25% -1 oct", dict(MONO, DcoWaveSaw=0, DcoWaveSub=1, DcoSubLevel=3), "Adds the octave above: more defined."),
        ("Mixed -1 oct", dict(MONO, DcoWaveSaw=0, DcoWaveSub=2, DcoSubLevel=3), "Strong upper partials: the brightest of the -1 octave positions."),
        ("Bright square -1 oct", dict(MONO, DcoWaveSaw=0, DcoWaveSub=3, DcoSubLevel=3), "Odd harmonics only, like the square, but with stronger upper ones."),
        ("Square -2 oct", dict(MONO, DcoWaveSaw=0, DcoWaveSub=4, DcoSubLevel=3), "Very low: for higher notes, rather than bass."),
        ("Pulse 25% -2 oct", dict(MONO, DcoWaveSaw=0, DcoWaveSub=5, DcoSubLevel=3), "Adds the octave above the sub, so it reads more clearly than the -2 octave square."),
    ]),
    ("Resonance", "A saw with the filter sweeping. Only the resonance changes.", [
        ("Resonance 0", dict(SWEEP), "A smooth sweep."),
        ("Resonance 4", dict(SWEEP, VcfResonance=0.4), "A clear peak travels with the sweep."),
        ("Resonance 8", dict(SWEEP, VcfResonance=0.8), "Strongly vocal. The low end drops noticeably."),
        ("Resonance 8 + BOOST", dict(SWEEP, VcfResonance=0.8, resonanceBoost=1), "A slightly stronger peak. Resonance goes higher still, and BOOST matters most at the top of its range."),
    ]),
    ("High-pass and bass boost", "A saw, played low. The filter has four positions, and 'off' is the second.", [
        ("Bass boost", dict(MONO, DcoRange=2, HpfCutoff=0), "A broad lift of about 6 dB up to 250 Hz."),
        ("Bass boost + ALT", dict(MONO, DcoRange=2, HpfCutoff=0, resonanceBoostFrequency=1), "A tighter peak around 80 Hz."),
        ("Off", dict(MONO, DcoRange=2), "Neutral."),
        ("HP 1", dict(MONO, DcoRange=2, HpfCutoff=2), "A gentle low cut."),
        ("HP 2", dict(MONO, DcoRange=2, HpfCutoff=3), "A strong low cut, down 13 dB at 200 Hz."),
    ]),
    ("Chorus", "A saw chord would mask the effect, so this is one note. Width isn't visible in a spectrogram: listen on headphones.", [
        ("Chorus off", dict(MONO), "Dry and centred."),
        ("Chorus, slow", dict(MONO, DcoChorusSwitch=1, ChorusRate=0.25), "Gentle width."),
        ("Chorus, fast", dict(MONO, DcoChorusSwitch=1, ChorusRate=0.8), "A quick shimmer: the string machine's trick."),
    ]),
    ("Unison", "Detune 0.20 and spread 0.80. Each voice count is one note played on one key.", [
        ("3 voices", dict(MONO, UnisonoVoices=0.1, UnisonoDetune=0.2, UnisonoSpread=0.8), "A clear thickening."),
        ("5 voices", dict(MONO, UnisonoVoices=0.5, UnisonoDetune=0.2, UnisonoSpread=0.8), "A wall, with some loss of pitch focus."),
        ("7 voices", dict(MONO, UnisonoVoices=1.0, UnisonoDetune=0.2, UnisonoSpread=0.8), "The maximum."),
    ]),
    ("Envelope and VCA mode", "The same filter sweep through the shared envelope, with a different amp mode.", [
        ("VCA Normal", dict(SWEEP, VcaEnvMode=0), "Amp and filter close together: a pluck."),
        ("VCA Gate", dict(SWEEP), "The amp holds and only the filter closes: the note keeps its weight."),
    ]),
]


def slug(text):
    return text.lower().replace(" ", "-").replace("%", "").replace("+", "and")


def spectrogram(audio, path):
    fig, ax = plt.subplots(figsize=(6.4, 1.7), dpi=100)
    ax.specgram(audio.mean(axis=0) + 1e-7, NFFT=2048, noverlap=1536, Fs=bank.SR, cmap=CMAP, vmin=-95, vmax=-22)
    ax.set_yscale("log")
    ax.set_ylim(40, 16000)
    ax.set_yticks([100, 1000, 10000], ["100 Hz", "1 kHz", "10 kHz"])
    ax.minorticks_off()
    ax.tick_params(colors="#808090", labelsize=8, length=0)
    ax.set_xlabel("Seconds", color="#808090", fontsize=8)
    for side in ax.spines.values():
        side.set_visible(False)
    fig.savefig(path, transparent=True, bbox_inches="tight")
    plt.close(fig)


def main():
    synth = Synth(bank.SR)
    os.makedirs(os.path.join(bank.ROOT, "docs", "html", "img", "gallery"), exist_ok=True)
    lines = ["# Sound gallery", "",
             "Hear and see what each waveform and key control does. Each sample is an A3 held for two seconds, "
             "changing only what's named. Every spectrogram uses the same scale, so you can compare them directly.", ""]
    for title, intro, items in GROUPS:
        lines += [f"## {title}", "", intro, ""]
        for name, params, text in items:
            synth.load_params(params)
            audio = synth.render(note(57, 0, 2.0), 2.4)
            key = f"{slug(title)}-{slug(name)}"
            write_mp3(audio, os.path.join(bank.ROOT, "audio", "gallery", key + ".mp3"))
            spectrogram(audio, os.path.join(bank.ROOT, "docs", "html", "img", "gallery", key + ".png"))
            lines += [f"**{name}.** {text} [Hear it](../audio/gallery/{key}.mp3)", "",
                      f"![Spectrogram of {name}](img/gallery/{key}.png)", ""]
            print(key, flush=True)
    with open(os.path.join(bank.ROOT, "tools", "guides", "gallery.md"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
