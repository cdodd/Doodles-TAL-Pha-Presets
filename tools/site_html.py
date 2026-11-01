"""Write the HTML docs to docs/html/. No external assets, so it works offline."""
import html
import os
import re
import shutil
from urllib.parse import quote

import markdown
import numpy as np

import bank

OUT = os.path.join(bank.ROOT, "docs", "html")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site_assets")
REPO = "https://github.com/cdodd/Doodles-TAL-Pha-Presets"
e = html.escape


def anchor(name):
    return name.lower().replace(" ", "-")


GUIDES = [("field-guide", "Field guide"), ("control-reference", "Control reference"), ("gallery", "Sound gallery"),
          ("sound-map", "Sound map"), ("kits", "Starter kits"), ("reaper-cheat-sheet", "Reaper cheat sheet")]


def nav(cats, active, patch_links=""):
    links = [f'<a href="index.html"{" aria-current=page" if active == "index" else ""}>Overview</a>',
             '<p class="nav-label">Patches</p>']
    for cat in cats:
        current = active == cat["slug"]
        links.append(f'<a href="{cat["slug"]}.html"{" aria-current=page" if current else ""}>{e(cat["category"])}</a>')
        if current:
            links.append(patch_links)
    links.append('<p class="nav-label">Guides</p>')
    links += [f'<a href="{slug}.html"{" aria-current=page" if active == slug else ""}>{label}</a>' for slug, label in GUIDES]
    return "\n".join(links)


def page(title, cats, active, body, patch_links=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="stylesheet" href="style.css">
<script>try{{var t=localStorage.getItem("theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body>
<header class="topbar">
  <a class="brand" href="index.html"><span>Doodles</span> TAL-Pha Presets</a>
  <button type="button" id="theme" class="ghost" aria-label="Switch between light and dark theme">Theme</button>
</header>
<div class="layout">
<nav class="sidebar" aria-label="Documentation">
{nav(cats, active, patch_links)}
</nav>
<main>
{body}
</main>
</div>
<script src="site.js"></script>
</body>
</html>
"""


def patch_url(name, cats, here):
    for cat in cats:
        if any(p["name"] == name for p in cat["patch"]):
            prefix = "" if cat["slug"] == here else f'{cat["slug"]}.html'
            return f"{prefix}#{anchor(name)}"
    return None


def pairing(pair, cats, here):
    name = e(pair["with"])
    if pair.get("external"):
        label = f"<strong>{name}</strong>"
    else:
        label = f'<a href="{patch_url(pair["with"], cats, here)}">{name}</a>'
    return f"<li>{label}<span class=\"why\">{e(pair['why'])}</span></li>"


def duration(s):
    return f"{s * 1000:.0f} ms" if s < 1 else f"{s:.1f} s"


def built_in_effects(patch):
    """Which built-in effects to keep and which to turn off, going by whether the patch's notes depend on them."""
    params, why = patch["params"], patch["why"]
    keep, optional = [], []
    for label, switch, prefixes in [("chorus", "DcoChorusSwitch", ("DcoChorusSwitch", "ChorusRate")),
                                    ("delay", "delayDryWet", ("delay",)), ("reverb", "reverbDryWet", ("reverb",))]:
        if float(params.get(switch, 0)) > 0:
            (keep if any(k.startswith(prefixes) for k in why) else optional).append(label)
    joined = lambda items: " and ".join(items) if len(items) < 3 else f"{items[0]}, {items[1]} and {items[2]}"
    parts = []
    if keep:
        parts.append(f"Built-in {joined(keep)}: part of this sound, so keep {'it' if len(keep) == 1 else 'them'}.")
    if optional:
        parts.append(f"Built-in {joined(optional)}: turn {'it' if len(optional) == 1 else 'them'} off if you're using your own.")
    return " ".join(parts)


def facts(patch, m):
    width = "Mono" if m["side_mid"] < 0.02 else f"Stereo, side/mid {m['side_mid']:.2f}"
    decay = "Holds while the key is down" if m["decay_s"] is None else f"Falls 20 dB in {duration(m['decay_s'])}"
    rows = [("Playing range", patch["range"]),
            ("Brightness", f"{m['centroid_hz']:.0f} Hz centroid"),
            ("Low energy", f"{m['low_energy_pct']:.0f}% below 150 Hz"),
            ("Attack", f"Half level in {m['attack_s'] * 1000:.0f} ms"),
            ("Decay", decay),
            *([("Held note", "Dies away")] if m["short_note"] else [
                ("Filter closes", f"{max(m['sweep_octaves'], 0):.1f} octaves"),
                ("Held level", f"{m['sustain_db']:.0f} dB from peak")]),
            ("Width", width),
            ("Mono sum", f"{m['mono_loss_db']:+.1f} dB"),
            ("Loudness", f"{m['lufs']:.1f} LUFS, peak {m['peak_db']:.1f} dBFS")]
    return '<dl class="facts">' + "".join(f"<div><dt>{a}</dt><dd>{e(b)}</dd></div>" for a, b in rows) + "</dl>"


def patch_card(cat, patch, cats, meas, patch_params):
    name = patch["name"]
    significant, other = patch_params(cat, patch)
    tags = "".join(f'<span class="tag">{e(t)}</span>' for t in patch["tags"])
    audio = "../../" + quote(bank.audio_rel(cat["slug"], name))
    preset = "../../" + quote(os.path.relpath(bank.preset_path(cat["category"], name), bank.ROOT))
    rows = "".join(f'<tr><th scope="row">{e(a)}</th><td class="value">{e(b)}</td><td>{e(c)}</td></tr>'
                   for a, b, c in significant)
    others = "; ".join(f"{e(a)} {e(b)}" for a, b in other)
    effects = built_in_effects(patch)
    mix = patch["mix"] + ([effects] if effects else [])
    return f"""<article class="patch" id="{anchor(name)}" data-tags="{e(' '.join(patch['tags']))}">
<header>
  <h2>{e(name)}</h2>
  <div class="tags">{tags}</div>
</header>
<p class="profile">{e(patch['profile'])}</p>
<div class="player">
  <audio controls preload="none" src="{audio}" aria-label="Preview of {e(name)}"></audio>
  <a class="ghost" href="{preset}" download>Preset file</a>
</div>
{facts(patch, meas[name])}
<h3>Significant parameters</h3>
<div class="table-wrap"><table class="params">
<thead><tr><th scope="col">Control</th><th scope="col">Value</th><th scope="col">Why</th></tr></thead>
<tbody>{rows}</tbody>
</table></div>
<p class="other"><strong>Other settings:</strong> {others}.</p>
<div class="columns">
  <section><h3>Performance</h3><p>{e(patch['performance'])}</p></section>
  <section><h3>How to use it</h3><p>{e(patch['use'])}</p></section>
  <section><h3>Mixing</h3><ul>{"".join(f"<li>{e(x)}</li>" for x in mix)}</ul></section>
  <section><h3>Pairings</h3><ul class="pairs">{"".join(pairing(p, cats, cat['slug']) for p in patch['pairings'])}</ul></section>
</div>
<h3>Tweak it</h3>
<ul class="tweaks">{"".join(f"<li><strong>{e(t['control'])}</strong><span>{e(t['result'])}</span></li>" for t in patch['tweaks'])}</ul>
</article>"""


def subnav(cat, on_recipe):
    prefix = f'{cat["slug"]}.html' if on_recipe else ""
    current = " aria-current=page" if on_recipe else ""
    links = [f'<a class="recipe-link" href="{cat["slug"]}-recipe.html"{current}>Build from init</a>']
    links += [f'<a href="{prefix}#{anchor(p["name"])}">{e(p["name"])}</a>' for p in cat["patch"]]
    return f'<div class="subnav">{"".join(links)}</div>'


def recipe_step(i, step):
    changes = ""
    if step["changes"]:
        rows = "".join(f'<li><span class="control">{e(a)}</span><span class="from">{e(b)}</span>'
                       f'<span class="arrow" aria-hidden="true">→</span><span class="sr">to</span>'
                       f'<span class="to">{e(c)}</span></li>' for a, b, c in step["changes"])
        changes = f'<ul class="changes">{rows}</ul>'
    alternative = ""
    if step.get("alternative"):
        alternative = f'<p class="alt"><strong>The other choice:</strong> {e(step["alternative"])}</p>'
    measures = ""
    if step["measures"]:
        rows = "".join(f"<li>{e(a)}: {e(b)} → <strong>{e(c)}</strong></li>" for a, b, c in step["measures"])
        measures = f'<ul class="measures" aria-label="Measured change from the previous step">{rows}</ul>'
    return f"""<li class="step">
<h2>{e(step['title'])}</h2>
{changes}
<p>{e(step['why'])}</p>
{alternative}
<div class="listen">
  <audio controls preload="none" src="../../{quote(step['audio'])}" aria-label="Step {i}: {e(step['title'])}"></audio>
  <p><strong>Listen for:</strong> {e(step['listen'])}</p>
  {measures}
</div>
</li>"""


def recipe_page(recipe, cat, cats):
    steps = "\n".join(recipe_step(i, s) for i, s in enumerate(recipe["steps"], 1))
    takeaways = "".join(f"<li>{e(x)}</li>" for x in recipe["takeaways"])
    branches = "".join(f'<li><a href="{cat["slug"]}.html#{anchor(b["to"])}">{e(b["to"])}</a>'
                       f'<span class="why">{e(b["how"])}</span></li>' for b in recipe["branch"])
    body = f"""<div class="recipe">
<h1>{e(recipe['title'])}</h1>
<p class="lede">{e(recipe['intro'])}</p>
<section class="install">
<h2>Setup</h2>
{markdown.markdown(recipe['setup'])}
<p>Each step's preview adds to the one before. Measurements compare it with the previous step.</p>
</section>
<ol class="steps">
{steps}
</ol>
<section class="install">
<h2>What to take away</h2>
<ul>{takeaways}</ul>
</section>
<h2 class="next">Where to go next</h2>
<p>Starting points for moving from <a href="{cat['slug']}.html#{anchor(recipe['patch'])}">{e(recipe['patch'])}</a> to another patch in the bank:</p>
<ul class="pairs">{branches}</ul>
</div>"""
    return page(f"{recipe['title']}: Doodles TAL-Pha Presets", cats, cat["slug"], body, subnav(cat, True))


def category_page(cat, cats, meas, patch_params):
    all_tags = sorted({t for p in cat["patch"] for t in p["tags"]})
    chips = '<button type="button" class="chip" aria-pressed="true" data-tag="">All</button>' + "".join(
        f'<button type="button" class="chip" aria-pressed="false" data-tag="{e(t)}">{e(t)}</button>' for t in all_tags)
    cards = "\n".join(patch_card(cat, p, cats, meas, patch_params) for p in cat["patch"])
    body = f"""<h1>{e(cat['category'])}</h1>
<p class="lede">{len(cat['patch'])} patches. Control values are as shown on the plugin panel. Times and frequencies
come from <a href="control-reference.html">measurements of the plugin</a>.</p>
<a class="callout" href="{cat['slug']}-recipe.html"><strong>New to this category?</strong> Build a patch from init, step by step, hearing each decision.</a>
<section class="install">
<h2>Mixing this category</h2>
<p>Starting points for every patch here. Each patch's own notes cover what's different about it.</p>
<ul>{"".join(f"<li>{e(x)}</li>" for x in cat['mix_defaults'])}</ul>
</section>
<div class="chips" role="group" aria-label="Filter by subgenre">{chips}</div>
{cards}"""
    return page(f"{cat['category']}: Doodles TAL-Pha Presets", cats, cat["slug"], body, subnav(cat, False))


def index_page(cats):
    total = sum(len(c["patch"]) for c in cats)
    rows = []
    for cat in cats:
        items = "".join(f'<a href="{cat["slug"]}.html#{anchor(p["name"])}">{e(p["name"])}</a>' for p in cat["patch"])
        rows.append(f'<section class="bank-row"><h2><a href="{cat["slug"]}.html">{e(cat["category"])}</a></h2><div class="names">{items}</div></section>')
    body = f"""<h1>Doodles TAL-Pha Presets</h1>
<p class="lede">{total} synthwave-style presets for <a href="https://tal-software.com/products/tal-pha">TAL-Pha</a>, an Alpha Juno II emulator synth
by TAL Software. Each one is documented so you can see how the sound works and how to use it. New to the synth? Start with the <a href="field-guide.html">field guide</a>.</p>
<p class="callout notice"><svg role="img" aria-label="Information" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 11v6M12 7h.01"/></svg><span>These presets and this documentation were generated using Claude Opus 5.5.</span></p>
<section class="install">
<h2>Install</h2>
<p>The steps are the same on Linux, macOS and Windows.</p>
<ol>
<li>Download <a href="{REPO}/releases/latest/download/Doodles-TAL-Pha-Presets.zip">Doodles-TAL-Pha-Presets.zip</a> and extract it.</li>
<li>In TAL-Pha, open the preset browser and click <strong>Open Folder…</strong>.</li>
<li>Copy the <strong>Doodles</strong> folder into the folder that opens.</li>
<li>In the preset browser, press <strong>Reload</strong> and filter by the <strong>Doodles</strong> bank.</li>
</ol>
<p>If you've cloned <a href="{REPO}">the repo</a>, skip step 1 and copy <code>presets/Doodles</code> instead.</p>
</section>
{"".join(rows)}
<section class="install">
<h2>Licence</h2>
<p>Released into the public domain under <a href="{REPO}/blob/main/LICENSE">CC0 1.0</a>: use it for anything, with no attribution needed and no warranty.</p>
<p>This project isn't affiliated with or endorsed by TAL Software. TAL-Pha is their product, and CC0 grants no rights in their name or software.</p>
</section>"""
    return page("Doodles TAL-Pha Presets", cats, "index", body)


def guide_page(slug, label, cats, source):
    body = markdown.markdown(source, extensions=["tables", "fenced_code"])
    body = re.sub(r'<a href="\.\./audio/([^"]+)">Hear it</a>',
                  lambda m: f'</p><audio controls preload="none" src="../../audio/{m.group(1)}"></audio><p class="gap">', body)
    body = body.replace('<p class="gap"></p>', "")
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    body = re.sub(r"<p>", '<p class="lede">', body, count=1)
    return page(f"{label}: Doodles TAL-Pha Presets", cats, slug, f'<div class="prose">{body}</div>')


MAP_X = (40, 16000)
MAP_Y = (0, 1.3)


def map_panel(cat, all_points, meas):
    w, h, left, bottom = 320, 190, 8, 26
    px = lambda hz: left + (w - left - 8) * (np.log10(min(max(hz, MAP_X[0]), MAP_X[1])) - np.log10(MAP_X[0])) / (np.log10(MAP_X[1]) - np.log10(MAP_X[0]))
    py = lambda s: (h - bottom) * (1 - min(s, MAP_Y[1]) / MAP_Y[1]) + 4
    grid = "".join(f'<line class="grid" x1="{px(hz):.1f}" x2="{px(hz):.1f}" y1="4" y2="{h - bottom + 4}"/>'
                   f'<text class="tick" x="{px(hz):.1f}" y="{h - 8}" text-anchor="middle">{label}</text>'
                   for hz, label in [(100, "100 Hz"), (1000, "1 kHz"), (10000, "10 kHz")])
    grid += f'<line class="grid" x1="{left}" x2="{w - 8}" y1="{py(0):.1f}" y2="{py(0):.1f}"/>'
    grid += (f'<text class="tick" x="{left + 2}" y="14">Wide</text>'
             f'<text class="tick" x="{left + 2}" y="{py(0) - 5:.1f}">Mono</text>')
    context = "".join(f'<circle class="ctx" cx="{px(c):.1f}" cy="{py(s):.1f}" r="2.5"/>' for c, s in all_points)
    hits = marks = ""
    for p in cat["patch"]:
        m = meas[p["name"]]
        tip = f"{p['name']}: {m['centroid_hz']:,.0f} Hz, width {m['side_mid']:.2f}"
        cx, cy = px(m["centroid_hz"]), py(m["side_mid"])
        href = f'{cat["slug"]}.html#{anchor(p["name"])}'
        # Hit areas go underneath every mark, so a neighbour's hit area can't cover a mark.
        hits += (f'<a class="dot" href="{href}" tabindex="-1" aria-hidden="true" data-tip="{e(tip)}">'
                 f'<circle class="hit" cx="{cx:.1f}" cy="{cy:.1f}" r="11"/></a>')
        marks += (f'<a class="dot" href="{href}" aria-label="{e(tip)}" data-tip="{e(tip)}">'
                  f'<circle class="mark" cx="{cx:.1f}" cy="{cy:.1f}" r="4.5"/></a>')
    return (f'<figure class="panel"><figcaption><a href="{cat["slug"]}.html">{e(cat["category"])}</a></figcaption>'
            f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{e(cat["category"])} patches by brightness and width">'
            f"{grid}{context}{hits}{marks}</svg></figure>")


def sound_map_page(cats, meas, table):
    points = [(m["centroid_hz"], m["side_mid"]) for m in meas.values()]
    panels = "".join(map_panel(c, points, meas) for c in cats)
    table_html = markdown.markdown(table, extensions=["tables"]).replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    body = f"""<div class="map-page"><h1>Sound map</h1>
<p class="lede">Every patch by brightness and stereo width, measured on its preview phrase. Each chart highlights one
category against the whole bank, so you can see where its patches sit and which ones will compete.</p>
<p>Left to right is darker to brighter. Bottom to top is mono to wide. Two patches close together will compete for the
same space, so when you layer them, separate them with EQ or panning. Hover over a dot for its name, or click it to open that patch.</p>
<div class="panels">{panels}</div>
<div id="tip" class="tip" hidden></div>
<h2>All patches</h2>
{table_html}</div>"""
    return page("Sound map: Doodles TAL-Pha Presets", cats, "sound-map", body)


def write_site(cats, meas, patch_params, recipes, guides, map_table):
    os.makedirs(OUT, exist_ok=True)
    for asset in ["style.css", "site.js"]:
        shutil.copy(os.path.join(ASSETS, asset), OUT)
    pages = {"index.html": index_page(cats), "sound-map.html": sound_map_page(cats, meas, map_table)}
    for slug, label in GUIDES:
        if slug != "sound-map":
            pages[slug + ".html"] = guide_page(slug, label, cats, guides[slug])
    for cat in cats:
        pages[cat["slug"] + ".html"] = category_page(cat, cats, meas, patch_params)
    by_category = {c["category"]: c for c in cats}
    for recipe in recipes:
        pages[recipe["slug"] + "-recipe.html"] = recipe_page(recipe, by_category[recipe["category"]], cats)
    for filename, content in pages.items():
        with open(os.path.join(OUT, filename), "w") as f:
            f.write(content)
    print("wrote", len(pages), "HTML pages")
