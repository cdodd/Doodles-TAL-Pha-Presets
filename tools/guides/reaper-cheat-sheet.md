# Reaper cheat sheet

Common synthwave mix moves using only Reaper's stock plugins. Settings are starting points: use your ears from there.

## Getting a preset

Add **TAL-Pha** to a track, click the file icon to open the preset browser, press **Reload**, and filter by the **Doodles** bank. Presets aim for about the same loudness, and most peak well below -3 dBFS. Free-running oscillators can move a peak by a few dB from one play to the next, so a few can go higher. Turn your track fader down rather than adding a limiter. Short, punchy patches such as stabs can't reach the target without clipping, so they sit a few dB quieter.

To hear a chord memory patch, hold a single note. To hear an arp patch, hold a chord. The arp and synced delays and LFOs are set to follow the host's tempo, but they've only been rendered at 120 BPM, so check them at your project's tempo.

## Sidechain the bass and pad to the kick

This is the pump that defines the style.

1. Open the kick track's routing (**Route** button) and add a send to the bass track.
2. Set the send's audio to **1/2 -> 3/4**. Reaper adds the extra channels for you.
3. Add **ReaComp** to the bass track and set **Detector input** to **Auxiliary L+R**.
4. Start with ratio 4:1, attack 1 ms and release 100 ms, then lower the threshold until you see 3-6 dB of reduction.

Repeat for the pad, with a longer release around 200-300 ms. Use the same send from the kick, or a ghost kick with its own output muted, if the real kick doesn't play on every beat.

## Gated reverb snare

The big 80s snare, and easier than it looks.

1. Create a new track called "Snare verb". Send the snare to it on **1/2 -> 1/2**, and also on **1/2 -> 3/4**.
2. On that track, add **ReaVerbate** at 100% wet with a large room size.
3. After it, add **ReaGate**, with **Detector input** set to **Auxiliary L+R**.
4. Set the threshold so the gate opens on each hit, hold around 150-250 ms and release around 20 ms.
5. Bring the track's fader up beneath the dry snare.

## Keep the low end mono

Steel Engine and Velvet Bass have some low-end stereo, and it can also come from chorus on other parts.

- Simplest: put **Midnight Sub** on its own mono track, then high-pass the wide patch at about 120 Hz with **ReaEQ**.
- Or lower the width overall with **JS: Stereo Width**, or turn the patch's chorus or unison spread down.

Check by pressing the mono button on your master track from time to time. These presets lose at most about 3 dB in mono.

## Basic EQ moves

Using **ReaEQ**:

| Part | High-pass | Other moves |
|---|---|---|
| Bass | 30 Hz | Small lift at 800 Hz to 1.5 kHz, for small speakers |
| Pad | 150-200 Hz | Dip 300-500 Hz if chords cloud |
| Lead | 200-300 Hz | Small lift at 2-3 kHz |
| Arp | 250 Hz | Keep it low in level rather than EQing it |
| Brass | 150 Hz | Lift at 1-2 kHz for bite |

## Delay and reverb on sends

The built-in effects are fine for one part, but a shared send ties a mix together and lets you turn off a patch's own effects.

- **ReaDelay:** set Length (musical) to **0.75** for a dotted 8th, or 0.5 for an 8th.
- **ReaVerbate** or **ReaVerb** with an impulse response, for a shared room.
- Tick **FX LOCK** in TAL-Pha if you want to keep your effects settings while browsing presets.

## Tape and saturation

**JS: Saturation** adds warmth and grit. Use a little on the bass, or on a bus with a high cut around 8 kHz from ReaEQ, for a cassette feel.

## Level check

Use **ReaLimit** on the master only for checking loudness at the end. If you're hitting it during the mix, turn the tracks down instead.
