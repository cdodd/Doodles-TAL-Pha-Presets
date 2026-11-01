# Field guide

How TAL-Pha is put together, what it can't do and how to get around that, and what values to start from for each type of sound. For measured numbers, see the [control reference](control-reference.html).

## Signal flow

```
DCO  ->  HPF  ->  VCF  ->  VCA  ->  effects
saw       |      24 dB      |       chorus, EQ, delay, reverb
pulse     |
sub       |      One envelope drives pitch, filter and amp.
noise     |      One LFO drives pitch and filter.   
```

Each voice runs through the same path. PWM has its own rate control, separate from the main LFO.

## What it can't do, and how to get around it

Most of the decisions in this bank come from these limits. If a patch's settings seem odd, it's probably working around one of them.

| Limit | Workaround | See it in |
|---|---|---|
| One envelope for pitch, filter and amp | VCA **Gate**: the amp follows the key, leaving the envelope to the filter and pitch | [Bass recipe](bass-recipe.html) |
| Envelope can't fall and then rise in plain ADSR terms | Use the extra stage: T1/L1, T2/L2, T3/L3 can go in either direction | [Sforzando](brass.html#sforzando) |
| LFO can't reach the amp, so no tremolo | Move the filter instead, with a deep LFO; a square wave chops the sound | [Gated Chord](chord.html#gated-chord) |
| No sidechain inside the synth | A synced saw LFO on the filter gives a similar pump | [Pulse Bloom](pad.html#pulse-bloom) |
| One filter | Use the HPF for the low end and the VCF for the top; the bell EQ can add a formant | [Retro Choir](pad.html#retro-choir) |
| Not an FM synth | Sync adds metallic overtones; open the filter only at the attack, to reveal them briefly | [Keys recipe](keys-recipe.html) |
| One oscillator per voice | Pulse Tune and Fine make the pulse a second source; chorus and unison add more | [Chrome Octave](bass.html#chrome-octave) |
| Pitch envelope leaves held notes off pitch with sustain above 0 | Set sustain to 0 with VCA Gate, so the note holds and the pitch returns | [Razor Fifth](lead.html#razor-fifth) |
| Chorus has no low-frequency limit | Keep it off low patches, or narrow the lows in your mix | [Velvet Bass](bass.html#velvet-bass) |

## The controls, in the order you'd reach for them

1. **Range, wave and voices.** Which register and how many notes? Mono for bass and most leads; 6-10 voices for pads and keys, as releases overlap.
2. **VCA mode.** Should the level follow the envelope (pluck, pad) or the key (bass, organ)?
3. **Envelope times and sustain.** This is usually what defines the instrument type: see the table below.
4. **Filter cutoff and envelope amount.** Start darker than you'd expect. Envelope amount is strong, and does nothing useful if sustain is at full.
5. **Velocity mode.** Normal-Dynamic is one of the strongest tone controls on the synth.
6. **Motion.** PWM, a slow LFO on the filter, or delayed vibrato.
7. **Width.** Chorus or unison, keeping low notes in mind.
8. **Space.** Delay and reverb. The delay is centred until you move its spread away from 0.00.
9. **Wheel.** Init sends the wheel to vibrato, which is usually too wide. Set it to what the patch actually needs.

## Typical values by instrument type

The median settings across this bank's 10 patches in each category: a sensible starting point rather than a rule. Values are as shown on the panel.

{{typical_values}}

Reading down the table shows what separates the categories. Bass leans on VCA Gate. Arps, plucks and keys have little or no sustain. Pads and strings sustain fully, with long attacks and releases, and pads have a darker filter than strings.

## Learning path

1. Follow the "Build from init" pages in the plugin. Each category has one, and each builds a patch from the init sound a step at a time, so you can hear what every change does. Different categories teach different parameters, so use them to learn the controls you're curious about. Start with [Bass](bass-recipe.html), which shows how VCA Gate lets the single envelope sweep the filter while the amp holds the note.
2. Listen to the [sound gallery](gallery.html), so that you know what each wave and control sounds like.
3. Follow the [Pluck recipe](pluck-recipe.html), the mirror image of the bass, then [Pad](pad-recipe.html) for motion and width.
4. Pick a [starter kit](kits.html) and write a short track, then use the [Reaper cheat sheet](reaper-cheat-sheet.html) to mix it.
5. Choose a preset you like and change one thing at a time using its "Tweak it" notes.
