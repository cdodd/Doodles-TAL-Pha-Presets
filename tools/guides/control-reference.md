# TAL-Pha control reference

What the controls actually do, measured by rendering the plugin (`tools/calibrate.py` and `tools/calibrate_controls.py`, raw data in
[`calibration.json`](../data/calibration.json) and [`calibration_controls.json`](../data/calibration_controls.json)). It fills gaps in the manual and corrects labels the plugin
reports wrongly. For how to use the controls and typical values by sound, see the [field guide](field-guide.html).

Panel values are the 0-10 scale the plugin displays, unless noted. Preset files store most of these as 0-1. A few read differently: DCO Env reads 0-127 (slider position 4.2 reads 53), delay and reverb mix read Off, then about -1.00 to +1.00, and delay tone, delay spread and reverb tone read -5 to +5.

Oscillators and effects run free, so repeat runs differ slightly, most of all in reverb tails (up to about 3 dB). Treat the figures here as typical values rather than exact ones.

## Corrections to labels and assumptions

| What you might assume | What was measured |
|---|---|
| Sub wave "OFF" means no sub | It's a **square one octave down**. Only **sub level 0** silences the sub. |
| A DCO range of 16' with the sub on is a good bass | The sub is an octave below the range, so for an A2 note it's at 27.5 Hz, too low to be useful. Use 8' + sub for this. |
| Key follow brightens as you go up | The pivot is around **C4**. At full follow the cutoff is correct at C4 and **2 octaves lower at C2**, so key follow darkens bass notes. Raise cutoff to compensate. |
| Oscillator sync locks the pulse to the saw | It syncs to the **sub oscillator**, so the waveform repeats an octave below the note. This is where sync patches get extra low growl. |
| Portamento mode labels ("ALWAYS", "Unknown") | Values are **Off / On (overlapping notes only) / All notes**, as the manual says. |
| Resonance boost label "Unknown" | File value 1 is the **BOOST** button being on. It's a display quirk. |
| Voices label "50.00" | File value N gives **N + 1 voices**, so 0 is mono and 11 is 12 voices. |
| Pulse position "SAW" differs from Saw | It has the same harmonic series as the plain saw. It's useful because it can be retuned and synced separately. |

## Filter

| Cutoff (panel) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Hz, approx. | 9 | 20 | 45 | 100 | 220 | 470 | 1.1k | 2.3k | 5k | 11k | 21k |

Cutoff roughly doubles for each 1.0 on the panel.

**Envelope amount is very strong.** With cutoff at 2 and sustain full: env 2 reaches about 210 Hz, env 4 about 930 Hz, env 6 about 4.3 kHz, env 8 about 20 kHz. So small changes matter.

**Velocity in Normal-Dynamic mode is also very strong.** With cutoff 2, env 6: velocity 30 reaches about 130 Hz, 64 about 440 Hz, 100 about 1.7 kHz, 127 about 4.5 kHz. Velocity programming is a main performance tool on this synth.

**Resonance.** How far the peak stands above the level an octave below it, and what the note loses. Peak height uses noise at cutoff 6; level uses a saw at C2 with cutoff 5.5:

| Resonance | 0 | 2.5 | 5 | 7.5 | 9 | 10 |
|---|---|---|---|---|---|---|
| Peak, dB | 1 | 2 | 9 | 16 | 21 | 24 |
| Peak with BOOST, dB | 1 | 2 | 8 | 18 | 25 | 29 |
| Saw level change, dB | 0 | -2 | -4 | -8 | - | -7 |
| Saw level change with BOOST, dB | 0 | -2 | -4 | -7 | - | -1 |

Resonance thins low notes, so turn the patch up to compensate. BOOST changes little below 7.5, and most at the top of the range, where it brings back nearly all the lost level.

**Self-oscillation.** The manual says BOOST can self-oscillate. In these tests, with resonance 10, BOOST on, cutoff 6 and the DCO silent, the output stayed around -68 dB. Faint noise made it ring, but not as a steady tone. Don't count on it as a sine source without trying it at your settings.

**Modulating the cutoff.** All measured from a cutoff of about 470 Hz or lower, as noted. The VCF LFO and wheel to VCF LFO share a scale. A slow square LFO shows the two extremes:

| VCF LFO | 1 | 2 | 4 | 6 | 10 |
|---|---|---|---|---|---|
| Cutoff range, Hz | 380-600 | 310-740 | 200-1.1k | 120-1.6k | 80-3.6k |

| Control | 1 | 2.5 | 5 | 10 |
|---|---|---|---|---|
| MW to VCF, wheel full, from 100 Hz | 210 Hz | 600 Hz | 3.9 kHz | 17.6 kHz |
| VCF AT, full pressure, from 220 Hz | - | 560 Hz | 1.4 kHz | 8.5 kHz |

Half pressure gives about half the movement in octaves.

## HPF and bass boost

Level change in dB compared with HPF off:

| Setting | 30-60 Hz | 60-120 | 120-250 | 250-500 | 500-1k | 1k-2k |
|---|---|---|---|---|---|---|
| Bass boost | +5 | +6 | +6 | +3 | +1 | 0 |
| Bass boost + ALT | +3 | +5 | +2 | 0 | 0 | 0 |
| HP 1 | -13 | -8 | -4 | -1 | 0 | 0 |
| HP 2 | -25 | -19 | -13 | -7 | -3 | -1 |

"Off" is the second position, not the first. HP 1 is a gentle low-cut, useful for thinning a sound inside the synth.

## Envelope times

Measured with Env Key follow at 0. The times are not linear: most usable settings are below 7.

| Panel | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| T1 attack, to 90% | 0 | 15 ms | 25 ms | 70 ms | 145 ms | 400 ms | 0.8 s | 1.8 s | 5 s |
| T3 decay, to -20 dB | 10 ms | 35 ms | 60 ms | 120 ms | 300 ms | 680 ms | 1.4 s | 3 s | 7.6 s |
| T4 release, to -20 dB | 10 ms | 35 ms | 50 ms | 120 ms | 290 ms | 760 ms | 1.5 s | 3.2 s | 8.1 s |

**There's only one envelope,** shared by filter, pitch and amp. VCA **Gate** gives the amp its own on/off behaviour, so the filter can sweep while the note stays loud.

**In Gate mode, T4 barely changes note length.** The amp closes with the key: the tail stayed around 35-45 ms at T4 settings from 0.8 to 6.0. In Normal mode, a T4 of 4.0 already leaves a tail of over 600 ms.

**T2 falls faster than T3.** At the same setting, T2 took about half as long to reach -20 dB (2: 30 ms, 3: 60 ms, 4: 135 ms, 5: 335 ms, 6: 680 ms).

**Env Key follow** changes every envelope time around C4. At T3 = 5, time to -20 dB:

| Key follow | C2 | C4 | C6 |
|---|---|---|---|
| 0 | 0.95 s | 0.95 s | 0.95 s |
| 5 | 1.9 s | 0.95 s | 0.5 s |
| 10 | 3.65 s | 0.95 s | 0.25 s |

So at full follow, each octave down doubles the time. Low notes linger and high notes snap shut, as on an acoustic instrument.

**Velocity to level.** In the VCA's Normal-Dynamic and Gate-Dynamic modes, compared with velocity 127: velocity 100 is -1.8 dB, 64 is -5.1 dB and 30 is -10 dB. In the plain modes, velocity makes no difference to level.

## Waveforms

Level of the first 8 harmonics in dB, relative to the strongest. These explain what the icons sound like:

| Wave | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | Character |
|---|---|---|---|---|---|---|---|---|---|
| Saw | 0 | -7 | -10 | -12 | -14 | -16 | -18 | -18 | Full, even series; the classic start |
| Saw 2 | -4 | 0 | -15 | -20 | -18 | -9 | -22 | -27 | Octave-heavy, hollow |
| Saw 3 | -7 | -13 | -15 | -16 | -15 | -15 | -10 | 0 | Top-heavy, buzzy |
| Saw 4 | -5 | 0 | -14 | -17 | -14 | -1 | -9 | 0 | Strong peaks at 2, 6, 8: bell-like |
| Square | 0 | off | -10 | off | -14 | off | -18 | off | Odd harmonics only: hollow |
| Pulse 25% | 0 | -4 | -10 | off | -14 | -13 | -18 | off | Nasal: every 4th harmonic missing |

Saw PW and Pulse PW depend on the PWM settings. The table's Saw 3 and Saw 4 are the panel's "SAW 3" and "SAW 4" (file values 4 and 5).

**Sub wave** has six positions. The names here are descriptive, as the panel shows icons. You can hear each one in the [sound gallery](gallery.html).

| File value | Name here | Fundamental | Upper harmonics |
|---|---|---|---|
| 0 | Square -1 oct (panel label: OFF) | 1 octave down | Odd only: 3rd -10 dB, 5th -15 dB |
| 1 | Pulse 25% -1 oct | 1 octave down | Adds a 2nd at -3 dB: 3rd -10 dB, 5th -15 dB |
| 2 | Mixed -1 oct | 1 octave down | Strong: 3rd and 4th -2 dB, 5th -7 dB |
| 3 | Bright square -1 oct | 1 octave down | Odd only, stronger than the square: 3rd -8 dB, 5th -10 dB |
| 4 | Square -2 oct | 2 octaves down | Odd only: 3rd -9 dB, 5th -14 dB |
| 5 | Pulse 25% -2 oct | 2 octaves down | Adds a 2nd at -3 dB: 3rd -9 dB, 5th -14 dB |

## Oscillator levels and pulse width

Level change from each mixer control, in dB:

| Setting | 10 | 7.5 | 5 | 2.5 | 1 |
|---|---|---|---|---|---|
| Saw Volume, Pulse Volume | 0 | -2.5 | -6 | -12 | -19 |
| VCA Level | 0 | -4.6 | -10.8 | -19.2 | - |

A square is 4.8 dB louder than a saw at the same setting. Sub and noise run from 0 to 3 on the panel. Their level alone, compared with a saw alone at full volume:

| Setting | 0.5 | 1 | 2 | 3 |
|---|---|---|---|---|
| Sub, dB | -14.5 | -8.5 | -2.5 | +1 |
| Noise, dB | -11.4 | -5.5 | +0.4 | +3.8 |

**Pulse width.** Of the pulse positions, only PULSE PW responds. SAW PW also changes with the PWM slider, but as a shift in harmonic balance rather than a width. With PWM Rate at 0, the PWM slider sets a fixed width:

| PWM | 0 | 2.5 | 5 | 7.5 | 10 |
|---|---|---|---|---|---|
| Width | 50% | 38% | 25% | 13% | 3% |

With PWM Rate above 0, the width sweeps between 50% and that value. The rate roughly doubles with each step:

| PWM Rate | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|
| Hz | 0.08 | 0.14 | 0.28 | 0.6 | 1.2 | 2.4 | 4.9 | 9.9 | 20 |

The sweep narrows at the fastest settings: PWM 6 covers 49% to 21% at most rates, but only 41% to 29% at rate 10.

**Pulse Tune, Fine and Mod.** Tune is exact in semitones, ±24. Fine reads -1 to +1, which is ±100 cents, and Master Fine Tune has the same range. The pulse's own Env and LFO mods read -1 to +1, grow with the square of the setting, and move only the pulse:

| Pulse mod setting | 0.05 | 0.1 | 0.25 | 0.5 | 1.0 |
|---|---|---|---|---|---|
| Env, peak pitch change, cents | - | 23 | 144 | 576 | 2304 |
| LFO, total swing, cents | 11 | 45 | 283 | 1131 | - |

Negative values mirror these. As with DCO Env, use sustain 0 if the pulse should return to pitch.

**Range** positions, from file value 0 to 3, are 4', 8', 16' and 32'.

## Unison

The panel offers Off, then 3 to 7 voices.

Stereo spread is wide even at low frequencies, and this is the main mix risk with unison on a bass. Side/mid ratio with 4 voices, detune 0.30, measured on a low note:

| Spread | 0 | 0.3 | 0.6 | 1.0 |
|---|---|---|---|---|
| Side/mid | 0 | 0.24 | 0.45 | 1.07 |

Unison voices run free, so each note starts differently. On Steel Engine the first 300 ms varies by about ±2 dB from note to note.

## Pitch depth: LFO, wheel and envelope

The DCO LFO slider and the mod wheel have very different scales. Total pitch swing on a held note, in cents:

| Setting | 0.5 | 1.0 | 2.0 | 4.0 |
|---|---|---|---|---|
| DCO LFO slider | 8 | 16 | 42 | 124 |
| MW to DCO LFO, wheel full up | 28 | 58 | 119 | - |

So 0.5 to 1.0 on the wheel is already a strong vibrato. **Init sets it to 1.0**, so a patch with an unused wheel should set it to 0 to avoid an unwanted wobble.

DCO envelope, peak pitch change: 1.0 is about 1 semitone, 2.0 about 2.4, 4.0 about 5.7, 7.0 about 13, and 10 about 30.

**A pitch envelope needs sustain at 0.** With sustain above 0, held notes stay off pitch. An inverted envelope at 4.2 with sustain 1.5 left held notes about 88 cents flat.

## LFO

**Rate** runs from 0.01 to 61 Hz, and the panel reading is accurate. Measured at settings reading 0.18, 0.95, 5.03 and 11.56 Hz, the real rate matched each. With **Sync** on, the control steps from 16/1 to 1/16T in straight and triplet values. Checks at 120 BPM (2/1T, 1/1T, 1/4T) landed on the right rate. 4/1 measured 0.11 Hz against an expected 0.125 Hz, which is close given that the test covers only about 1.5 of its cycles.

**Waveforms:**

| Wave | Pitch movement at the same depth | Use |
|---|---|---|
| Triangle | Even rise and fall, ±78 cents | General vibrato and sweeps |
| Sine | Rounder, ±83 cents | Vibrato |
| Saw | Slow rise, then a sudden drop, ±75 cents | Rhythmic pumps. INV flips it to a sudden rise and slow fall |
| REC | Jumps between two values, ±84 cents | Trills and gates |
| S&H | Random steps, about -150 to +90 cents | Random filter and pitch patterns |
| Noise | Tiny jitter, about 4 cents at DCO LFO 4 and 18 cents at 10 | Slight instability only |

**Noise isn't a slow random.** Its movement didn't change with the Rate control, and on the filter it swung under 1 dB where a triangle at the same depth swung 10 to 20 dB. Use S&H for audible randomness.

**Delay** applies to both pitch and filter. The vibrato reaches full depth at about the time the panel shows: readings of 0.40, 0.98 and 2.37 s reached 90% by about 0.5, 1.1 and 2.5 s, measured with a 0.4 s window. The panel reads 0 to 34 s.

**Trig.** With it off, the LFO runs free, so each note starts at a different point in the cycle: repeated notes began at pitch offsets from -75 to +74 cents. With it on, each began within 3 cents of the same point. Use Trig for anything that must repeat identically, such as a pluck's wobble.

## Aftertouch and pitch bend

Aftertouch responds to both channel and polyphonic pressure. All three amounts scale with pressure, so half pressure gives about half the movement.

| Amount, at full pressure | 2.5 | 5 | 10 |
|---|---|---|---|
| DCO AT: vibrato swing added, cents | 105 | 209 | 419 |
| VCA AT: level added, from VCA Level 5, dB | +1.9 | +3.5 | +6 |

DCO AT works with DCO LFO at 0, and it uses the LFO's rate and wave. For the filter, see VCF AT above.

**Bend range** is exact, from 0 to 12 semitones in both directions.

## Portamento

Time to cover 90% of the interval, in seconds:

| Time | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Octave | 0.03 | 0.05 | 0.09 | 0.19 | 0.44 | 0.97 | 1.75 | 2.5 |
| Two octaves | 0.05 | 0.09 | 0.18 | 0.39 | 0.86 | 1.9 | 3.5 | 4.8 |
| Octave, time mode on | 0.04 | 0.08 | 0.15 | 0.32 | 0.73 | 1.6 | 3 | 4 |
| Two octaves, time mode on | 0.04 | 0.08 | 0.15 | 0.32 | 0.72 | 1.6 | 2.9 | 3.9 |

By default the slide has a constant speed, so a wider leap takes longer. With the `portamento_time_mode` parameter on, every slide takes the same time whatever the interval. It's listed among the plugin's automation parameters. Its panel label hasn't been confirmed.

## Chord memory

Notes are stored relative to C4, then transposed by whichever key you play. Each key sounds the whole chord in parallel. You need at least as many voices as chord notes: in mono, only the top note plays.

## Chorus

The chorus is only on or off: file values above 1 sound identical to 1. The rate control sets how fast and how far the pitch wobbles, which is why a slow setting adds gentle width and a fast one gives the obvious ensemble effect that the string patches rely on. It didn't give a single clean rate in Hz, so this table shows the wobble on one channel at A4:

| Chorus Rate | 0-4 | 5 | 6 | 7.5 | 9 | 10 |
|---|---|---|---|---|---|---|
| Swing, cents | 15-18 | 34 | 69 | 261 | 334 | 474 |

Width depends on the note: side/mid is 0.34 at C2 and 0.65 at A4. Summing to mono costs 0.4 dB at C2 and 1.6 dB at A4.

## Delay

Time follows the panel reading at 120 BPM, synced (1/16 to 4/1., in straight, triplet and dotted values) or free (0.04 to 4 s).

**Mix.** Level compared with the dry note at mix 0.00 or lower, in dB:

| Mix | -0.80 | -0.40 | 0.00 | +0.40 | +0.60 | +0.80 | +1.00 |
|---|---|---|---|---|---|---|---|
| Dry note | 0 | 0 | 0 | -4.5 | -8 | -14 | Silent |
| First echo | -20 | -11 | -6.5 | -3.6 | -2.5 | -1.5 | -1 |

The echo overtakes the note at about +0.40. At +1.00 the dry note is gone.

**Feedback.** Level change per repeat:

| Feedback | 2 | 4 | 6 | 8 | 10 |
|---|---|---|---|---|---|
| dB per repeat | -14 | -8 | -5 | -2.4 | -0.5 |

At 10 the repeats barely fade, so they'll keep building up if you keep playing.

**Tone** is 0.00 at neutral. Darker settings also lower the echo. With a noise source, the echo's spectral centroid and level were:

| Tone | -5 | -2.5 | 0 | +2.5 | +5 |
|---|---|---|---|---|---|
| Centroid | 2.5 kHz | 5.8 kHz | 7.7 kHz | 9 kHz | 11 kHz |
| Echo level, dB | -6.4 | -1.5 | 0 | -2.8 | -3.2 |

**Spread** is 0.00 at the centre, with echoes exactly centred and no added width. Both directions add width, and negative values mirror positive ones. It rotates the echoes rather than alternating them, so **it can't produce a clean left-right ping-pong.** This table shows how much louder each of the first six echoes is on the left, in dB, at feedback 9. A minus means louder on the right:

| Spread | 1st | 2nd | 3rd | 4th | 5th | 6th | Side/mid |
|---|---|---|---|---|---|---|---|
| 0.00 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| +0.50 | 4 | 9 | 10 | 10 | 9 | 9 | 1.05 |
| +1.00 | 7 | 9 | 9 | 8 | 8 | 7 | 0.98 |
| +2.00 | 10 | 9 | 8 | -2 | 7 | 6 | 0.92 |
| +2.50 | 9 | 10 | -1 | 6 | 7 | -3 | 0.86 |
| +3.00 | 13 | 2 | 9 | 9 | 5 | 8 | 0.98 |
| +4.00 | 15 | 13 | -3 | 10 | 10 | -7 | 0.91 |
| +5.00 | 1 | 0 | -2 | -3 | -5 | -6 | 0.54 |

Small settings give the widest result, with echoes steadily to one side. The pattern changes with feedback. For a true ping-pong, use a dedicated delay plugin in Reaper.

## Reverb

**Size** sets the tail. Time to fall 40 dB from just after the note:

| Size | 0-2 | 4 | 6 | 8 | 10 |
|---|---|---|---|---|---|
| Time | 0.3 s | 0.9 s | 1.7 s | 3.6 s | Over 14 s |

Size 10 didn't fade by 40 dB within the 14 s test, so treat it as a freeze-like effect.

**Pre-delay** adds to a built-in gap of about 35 ms: readings of 0, 90, 250 and 489 ms gave first sound at 36, 125, 285 and 525 ms.

**Tone** has a large effect, with a default of -2.00. With a noise source, the tail's spectral centroid was:

| Tone | -5 | -2 | 0 | +2 | +5 |
|---|---|---|---|---|---|
| Centroid | 170 Hz | 2.8 kHz | 4.9 kHz | 5.2 kHz | 8.4 kHz |

At -5 the tail is also about 12 dB quieter, so it nearly disappears.

**Mix.** Held-note level barely changes, so raising the mix mostly adds tail and width:

| Mix | -0.40 | 0.00 | +0.40 | +0.60 | +0.80 |
|---|---|---|---|---|---|
| Tail level, dB | -44 | -36 | -25 | -25 | -21 |
| Side/mid, held note | 0.09 | 0.24 | 0.44 | 0.79 | 0.90 |

At low mixes the reverb adds little width, so chorus, unison and delay spread are the main sources.

## Bell EQ

**Gain** runs from -24 to +24 dB, and the measured boost matched the reading to within about 0.7 dB. **Freq** runs from 20 Hz to 20 kHz on an uneven scale. The measured peak fell within about 7% of the reading at 181 Hz, 1268 Hz and 4817 Hz. **Q** runs from 0.025 to 40. The width of the boost, measured at half its gain, was:

| Q | 0.23 | 0.48 | 1 | 2.1 | 4.4 | 9.1 |
|---|---|---|---|---|---|---|
| Width, octaves | 4 | 2.4 | 1.2 | 0.6 | 0.3 | 0.16 |

## Voice tuning and round robin

The VT panel offsets each voice. These are the extremes of each slider, applied to every voice at once. File values run from 0 to 1, with 0.5 at the centre:

| Slider | Low end | Quarter | Centre | Three quarters | High end |
|---|---|---|---|---|---|
| Detune | -50 cents | -6.5 cents | 0 | +6.4 cents | +50 cents |
| Cutoff, from 470 Hz | 20 Hz | 305 Hz | 460 Hz | 790 Hz | 18 kHz |
| Pan | Hard left | 6.6 dB left | Centre | 6.6 dB right | Hard right |
| Attack, Decay, Release times | About × 1.9 | - | × 1 | - | About × 0.66 |

Detune and cutoff are very fine near the centre and very coarse at the ends, so small moves are all you need.

**Round robin.** With it off, repeated notes reuse the same voice, so voice tuning can't vary from note to note: eight repeats all stayed at one voice's -50 cents. With it on, they cycled through all the voices. Turn it on with voice tuning if you want repeated notes to differ.

## Arpeggiator

**Modes,** on a held C-E-G:

| Mode | Order |
|---|---|
| Up | C E G C E G |
| Down | C G E C G E |
| U&D | C E G E C E G E |
| U&D II | Same as U&D in this test |
| Random | Varies |

**Rate.** With no sync, the panel reading in Hz was accurate from 1.16 to 5.79 Hz. The range is 0.5 to 25 Hz. With sync, the control steps from 1/2 to 1/64T, and 1/4, 1/8, 1/16 and 1/16T all ran at the right speed at 120 BPM.

**SYNC and SYNC HOST** behaved identically here, counting from the note. The test renders have no transport, so any difference that depends on the host's position needs checking in Reaper.

## Other notes

- **Arp range:** file value N gives N + 1 octaves, whatever the plugin's label says.
- **VCA Gate ignores attack:** the amp opens at once, so T1 only shapes the filter and pitch.
- **Volume:** about 12 dB per doubling. 0.5 is 12 dB below 1.0.
- **Chorus** adds stereo content at low notes too, as there's no way to limit it to higher frequencies.
- **No direct tremolo:** the LFO reaches pitch and filter only.
- **DC offset:** notes begin with a small DC step, which is harmless, but it can mislead measurements of very low level.
- **Testing outside a DAW:** plugin renders start with a transient on the very first sample, so test notes need a short pre-roll. The render's tempo is 120 BPM. The delay also needs about 0.5 s after a preset loads. A note sooner than that, with mix below +1.00, gets early echoes.

## Not measured

These don't affect the sound of a patch in a way these tests could check, or need things a test render doesn't have, so what the manual says is all there is here:

- **MPE, MTS and .tun microtuning, and sysex:** see the manual.
- **FX Lock, Hold and MIDI Learn:** panel and host features.
- **Clean DCO:** the manual says you probably won't hear it. It removes the small DC step mentioned above.
- **The chord memory's mono mode** (`chord_original_mono_mode`): not tested.
