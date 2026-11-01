"""Read, write and load TAL-Pha .talalpha presets.

A preset is XML. Plugin state is the same XML wrapped in JUCE's "VC2!" binary
header, itself base64-encoded inside a <VST3PluginState> document, which is how
a preset file can be pushed through the plugin's real state loader.
"""
import copy
import os
import re
import struct
import xml.etree.ElementTree as ET

PLUGIN_PATH = os.path.expanduser("~/.vst3/TAL-Pha.vst3")
PREROLL = 0.3
_ALPHABET = ".ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+"


def _juce_b64_decode(text):
    size, body = text.split(".", 1)
    size = int(size)
    out = bytearray(size)
    bit = 0
    for char in body:
        value = _ALPHABET.index(char)
        for i in range(6):
            if bit >= size * 8:
                break
            if value >> i & 1:
                out[bit >> 3] |= 1 << (bit & 7)
            bit += 1
    return bytes(out)


def _juce_b64_encode(data):
    chars = []
    for k in range((len(data) * 8 + 5) // 6):
        value = 0
        for i in range(6):
            bit = k * 6 + i
            if bit < len(data) * 8 and data[bit >> 3] >> (bit & 7) & 1:
                value |= 1 << i
        chars.append(_ALPHABET[value])
    return f"{len(data)}." + "".join(chars)


def _vc2(xml_bytes):
    return b"VC2!" + struct.pack("<I", len(xml_bytes)) + xml_bytes


def _unwrap_vc2(blob):
    size = struct.unpack("<I", blob[4:8])[0]
    return blob[8 : 8 + size]


def plugin_state_xml(plugin):
    """Return the plugin's current <tal> XML as text."""
    outer = _unwrap_vc2(plugin.raw_state).decode()
    component = _juce_b64_decode(re.search(r"<IComponent>([^<]*)</IComponent>", outer).group(1))
    start = component.index(b"VC2!")
    return _unwrap_vc2(component[start:]).decode()


def load_xml_into_plugin(plugin, xml_bytes):
    """Push preset XML through the plugin's own state loader."""
    outer = _unwrap_vc2(plugin.raw_state).decode()
    wrapped = "<IComponent>" + _juce_b64_encode(_vc2(xml_bytes)) + "</IComponent>"
    outer = re.sub(r"<IComponent>[^<]*</IComponent>", lambda _: wrapped, outer)
    plugin.raw_state = _vc2(outer.encode())


def load_plugin():
    from pedalboard import load_plugin as _load

    return _load(PLUGIN_PATH)


def build_preset(template_root, name, params, *, bank, category, author, description,
                 tags, chord=None, voice_tuning=None):
    """Return preset XML bytes: the template with `params` applied.

    `params` uses the attribute names and units stored in preset files.
    `chord` is up to 6 MIDI notes for chord memory; `voice_tuning` is a list of
    per-voice attribute dicts.
    """
    root = copy.deepcopy(template_root)
    rel = f"{bank}/{category}/{name}.talalpha"
    root.attrib.update(presetName=name, path=rel, author=author, description=description,
                       tags=" ".join(tags), soundbank=bank)
    program = root.find("programs/program")
    unknown = [k for k in params if k not in program.attrib]
    if unknown:
        raise KeyError(f"{name}: unknown parameters {unknown}")
    program.attrib.update(path=rel, programname=name)
    program.attrib.update({k: repr(float(v)) for k, v in params.items()})
    if chord is not None:
        chord_el = program.find("Chord")
        for i in range(6):
            chord_el.set(f"midiNote{i}", str(chord[i] if i < len(chord) else -1))
    if voice_tuning is not None:
        for el, values in zip(program.find("voicetunings"), voice_tuning):
            el.attrib.update({k: repr(float(v)) for k, v in values.items()})
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode").encode()


TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.xml")


def load_template():
    return ET.parse(TEMPLATE_PATH).getroot()


def note(pitch, start, end, velocity=100):
    """MIDI events for one note, for use with Synth.render."""
    from mido import Message

    return [Message("note_on", note=pitch, velocity=velocity, time=start),
            Message("note_off", note=pitch, time=end)]


class Synth:
    """A loaded TAL-Pha, always configured through its real state loader."""

    def __init__(self, sample_rate=44100):
        self.plugin = load_plugin()
        self.sample_rate = sample_rate
        self.template = load_template()

    def load_params(self, params, **kwargs):
        xml = build_preset(self.template, "test", params, bank="t", category="t", author="",
                           description="", tags=[], **kwargs)
        load_xml_into_plugin(self.plugin, xml)

    def load_file(self, path):
        with open(path, "rb") as f:
            load_xml_into_plugin(self.plugin, f.read())

    def render(self, midi, duration):
        """Render MIDI; returns (channels, samples).

        Includes a pre-roll, trimmed from the result: a note on the very first
        sample picks up a startup transient that a real host never produces.
        """
        midi = sorted((m.copy(time=m.time + PREROLL) for m in midi), key=lambda m: m.time)
        audio = self.plugin(midi, duration=duration + PREROLL, sample_rate=self.sample_rate,
                            num_channels=2, buffer_size=256, reset=True)
        return audio[:, int(PREROLL * self.sample_rate) :]
