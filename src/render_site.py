"""Stap 3: de statische site bouwen.

Leest data/jobs_scored.json en schrijft public/index.html in eenvoudig
Nederlands. Geen JavaScript-framework; wel een klein beetje vanilla JS voor
client-side filteren, zoeken en sorteren (alles staat al in de HTML, JS toont
of verbergt alleen).

Per vacature tonen we score, label, het gematchte zoekprofiel, kenmerken
(locatie, werkvorm, salaris) als chips, en inklapbare matchredenen. Onbekende
waarden laten we weg in plaats van "niet vermeld" te tonen.

Gebruik:  python3 src/render_site.py
"""

import datetime
import html
import json
import os
import re

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
PUBLIC_DIR = os.path.join(PROJECT_DIR, "public")

DREMPEL = 50  # score waarboven een vacature standaard als topmatch telt

LABEL_KLEUR = {
    "Zeer interessant": "#1a7f37",
    "Interessant": "#0b5cad",
    "Mogelijk interessant": "#9a6700",
    "Lage match": "#6b6b6b",
}

GENERIEK_BEDRIJF = {"", "onbekend bedrijf", "onbekend"}
GENERIEK_LOCATIE = {"", "onbekend", "nederland", "the netherlands", "holland"}


def e(tekst):
    return html.escape(str(tekst or ""))


# --------------------------------------------------------------------------
# Datum
# --------------------------------------------------------------------------

def parse_datum(s):
    """Best-effort datum-parser. Geeft een date of None."""
    s = (s or "").strip()
    if not s:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", s)
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def datum_label(d, vandaag):
    """Relatieve datumtekst ('Vandaag', '3 dagen geleden', anders dd-mm-jjjj)."""
    if not d:
        return ""
    delta = (vandaag - d).days
    if delta < 0:
        return d.strftime("%d-%m-%Y")
    if delta == 0:
        return "Vandaag"
    if delta == 1:
        return "Gisteren"
    if delta <= 30:
        return f"{delta} dagen geleden"
    return d.strftime("%d-%m-%Y")


# --------------------------------------------------------------------------
# Dedup op inhoud
# --------------------------------------------------------------------------

def _norm(s):
    return " ".join((s or "").strip().lower().split())


def dedup_inhoud(vacatures):
    """Voeg duplicaten samen, ook over bronnen en steden heen.

    Aggregators bieden dezelfde vacature onder meerdere URL's, steden en bronnen
    aan. Twee gevallen:
    - Bekend bedrijf: dedup op (titel, bedrijf), locatie genegeerd. Zo vallen
      'rol X bij bedrijf Y' in meerdere steden samen tot één kaart.
    - Onbekend bedrijf: dedup op (titel, locatie) — voorzichtiger, want we kunnen
      losse werkgevers niet uit elkaar houden.
    Bij een botsing houden we de vacature met de hoogste score (en dus meestal
    de versie in een zoekgebied).
    """
    beste, volgorde = {}, []
    for v in vacatures:
        bedrijf = _norm(v.get("bedrijf"))
        if bedrijf and bedrijf not in GENERIEK_BEDRIJF:
            sleutel = ("b", _norm(v.get("titel")), bedrijf)
        else:
            sleutel = ("t", _norm(v.get("titel")), _norm(v.get("locatie")))
        if sleutel not in beste:
            beste[sleutel] = v
            volgorde.append(sleutel)
        elif v.get("score", 0) > beste[sleutel].get("score", 0):
            beste[sleutel] = v
    return [beste[s] for s in volgorde]


# --------------------------------------------------------------------------
# Kaart
# --------------------------------------------------------------------------

def chip(tekst, klasse="chip", titel=""):
    t = f" title='{e(titel)}'" if titel else ""
    return f"<span class='{klasse}'{t}>{e(tekst)}</span>"


def vacature_html(v, vandaag):
    titel = e(v.get("titel"))
    url = e(v.get("url"))
    score = v.get("score", 0)
    label = v.get("label", "")
    kleur = LABEL_KLEUR.get(label, "#6b6b6b")
    laag = 1 if score < DREMPEL else 0

    bedrijf = (v.get("bedrijf") or "").strip()
    locatie = (v.get("locatie") or "").strip()
    bron = (v.get("bron") or "").strip()
    d = parse_datum(v.get("datum"))
    datum_iso = d.isoformat() if d else ""
    datum_mooi = datum_label(d, vandaag)

    hybride = v.get("hybride")
    hybride_attr = "true" if hybride is True else ("false" if hybride is False else "onbekend")

    # Kenmerk-chips: alleen tonen wat we echt weten (geen ruis).
    chips = [chip(v.get("profiel"), "chip chip-profiel")] if v.get("profiel") else []
    if locatie and locatie.lower() not in GENERIEK_LOCATIE:
        chips.append(chip("📍 " + locatie))
    if hybride is True:
        chips.append(chip("🏠 Hybride", "chip chip-hybride"))
    if v.get("salaris_indicatie"):
        kort = v["salaris_indicatie"].replace(" bruto p/m (40u, geschat)", " p/m")
        chips.append(chip("💶 " + kort, "chip", titel=v["salaris_indicatie"]))
    if datum_mooi:
        chips.append(chip("🕑 " + datum_mooi, "chip chip-datum", titel=datum_iso))
    chips_html = "<div class='chips'>" + "".join(chips) + "</div>" if chips else ""

    # Meta-regel (bedrijf + bron), zonder onbekende waarden.
    meta_delen = []
    if bedrijf and bedrijf.lower() not in GENERIEK_BEDRIJF:
        meta_delen.append(e(bedrijf))
    if bron:
        meta_delen.append("Bron: " + e(bron))
    meta_html = f"<p class='meta'>{' &middot; '.join(meta_delen)}</p>" if meta_delen else ""

    # Inklapbare matchredenen / waarschuwingen.
    blokken = []
    redenen = v.get("redenen", [])
    if redenen:
        items = "".join(f"<li>{e(r)}</li>" for r in redenen)
        blokken.append(
            "<details class='match'><summary>Waarom deze match?</summary>"
            f"<ul>{items}</ul></details>"
        )
    waarschuwingen = v.get("waarschuwingen", [])
    if waarschuwingen:
        items = "".join(f"<li>{e(w)}</li>" for w in waarschuwingen)
        blokken.append(f"<div class='waarschuwing'><strong>Let op</strong><ul>{items}</ul></div>")
    dealbreakers = v.get("dealbreakers", [])
    if dealbreakers:
        items = "".join(f"<li>{e(dd)}</li>" for dd in dealbreakers)
        blokken.append(f"<div class='dealbreaker'><strong>Dealbreakers</strong><ul>{items}</ul></div>")

    titel_html = f"<a href='{url}' target='_blank' rel='noopener'>{titel}</a>" if url else titel
    knop = (
        f"<a class='knop' href='{url}' target='_blank' rel='noopener'>Bekijk vacature &rarr;</a>"
        if url else ""
    )

    zoek = e(" ".join([v.get("titel", ""), bedrijf, locatie]).lower())

    return f"""
    <article class="vacature" data-score="{score}" data-laag="{laag}"
      data-profiel="{e(v.get('profiel'))}" data-bron="{e(bron)}"
      data-hybride="{hybride_attr}" data-datum="{e(datum_iso)}" data-zoek="{zoek}">
      <div class="kop">
        <span class="score" style="--kleur:{kleur}" title="{e(label)}">{score}</span>
        <div class="kop-tekst">
          <h2>{titel_html}</h2>
          <span class="label" style="color:{kleur}">{e(label)}</span>
        </div>
      </div>
      {meta_html}
      {chips_html}
      {''.join(blokken)}
      {knop}
    </article>
    """


# --------------------------------------------------------------------------
# Hoofdprogramma
# --------------------------------------------------------------------------

def _laad(pad):
    if os.path.exists(pad):
        with open(pad, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def main():
    scored_pad = os.path.join(DATA_DIR, "jobs_scored.json")
    if not os.path.exists(scored_pad):
        print("[render] data/jobs_scored.json ontbreekt. Draai eerst score_jobs.py.")
        return

    vacatures = dedup_inhoud(_laad(scored_pad))
    # Sorteer op score (hoog -> laag), dan op nieuwste datum.
    vandaag = datetime.date.today()
    vacatures.sort(
        key=lambda v: (v.get("score", 0), (parse_datum(v.get("datum")) or datetime.date.min).isoformat()),
        reverse=True,
    )

    top = [v for v in vacatures if v.get("score", 0) >= DREMPEL]
    laag = [v for v in vacatures if v.get("score", 0) < DREMPEL]

    aantal_afgewezen = len(_laad(os.path.join(DATA_DIR, "rejected_jobs.json")))
    aantal_opgehaald = len(_laad(os.path.join(DATA_DIR, "jobs_raw.json")))
    datum_nu = vandaag.strftime("%d-%m-%Y")

    # Filteropties uit de data afleiden.
    profielen = sorted({v.get("profiel", "") for v in vacatures if v.get("profiel")})
    bronnen = sorted({(v.get("bron") or "").strip() for v in vacatures if (v.get("bron") or "").strip()})
    profiel_opties = "".join(f"<option value='{e(p)}'>{e(p)}</option>" for p in profielen)
    bron_opties = "".join(f"<option value='{e(b)}'>{e(b)}</option>" for b in bronnen)

    statchips = (
        "<div class='stats'>"
        f"<div class='stat'><span class='stat-getal'>{aantal_opgehaald}</span><span class='stat-label'>opgehaald</span></div>"
        f"<div class='stat'><span class='stat-getal'>{len(top)}</span><span class='stat-label'>topmatches</span></div>"
        f"<div class='stat'><span class='stat-getal'>{len(laag)}</span><span class='stat-label'>lage matches</span></div>"
        f"<div class='stat'><span class='stat-getal'>{aantal_afgewezen}</span><span class='stat-label'>afgewezen</span></div>"
        "</div>"
    )

    kaarten = "".join(vacature_html(v, vandaag) for v in (top + laag))
    if not (top or laag):
        kaarten = "<p class='leeg'>Nog geen matches gevonden.</p>"

    filterbalk = f"""
    <div class="filters">
      <input type="search" id="zoek" placeholder="Zoek op functie, bedrijf of plaats&hellip;" aria-label="Zoeken">
      <select id="f-profiel" aria-label="Zoekprofiel"><option value="">Alle zoekprofielen</option>{profiel_opties}</select>
      <select id="f-bron" aria-label="Bron"><option value="">Alle bronnen</option>{bron_opties}</select>
      <select id="f-sort" aria-label="Sorteren">
        <option value="score">Sorteer: hoogste score</option>
        <option value="datum">Sorteer: nieuwste eerst</option>
      </select>
      <label class="checkbox"><input type="checkbox" id="f-hybride"> Alleen hybride</label>
      <label class="checkbox"><input type="checkbox" id="f-laag"> Lage matches tonen</label>
    </div>
    <p class="teller-regel"><strong id="teller">{len(top)}</strong> vacatures getoond</p>
    """

    pagina = f"""<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vacature Radar</title>
  <style>
    :root {{ --rand: #e3e3e6; --grijs: #6b6b72; --blauw: #0b5cad; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      max-width: 880px; margin: 0 auto; padding: 1rem; color: #1a1a1a;
      background: #f4f5f7; line-height: 1.5; }}
    header {{ margin-bottom: 1rem; }}
    h1 {{ margin: 0 0 0.2rem; font-size: 1.6rem; }}
    .uitleg {{ color: var(--grijs); font-size: 0.95rem; margin: 0; }}

    .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.6rem; margin: 1rem 0; }}
    .stat {{ background: #fff; border: 1px solid var(--rand); border-radius: 10px;
      padding: 0.6rem; text-align: center; }}
    .stat-getal {{ display: block; font-size: 1.4rem; font-weight: 700; }}
    .stat-label {{ font-size: 0.75rem; color: var(--grijs); text-transform: uppercase; letter-spacing: 0.03em; }}

    .filters {{ position: sticky; top: 0; z-index: 5; display: flex; flex-wrap: wrap; gap: 0.5rem;
      background: #f4f5f7; padding: 0.6rem 0; border-bottom: 1px solid var(--rand); }}
    .filters input[type=search], .filters select {{ padding: 0.45rem 0.6rem; border: 1px solid var(--rand);
      border-radius: 8px; font-size: 0.9rem; background: #fff; }}
    .filters input[type=search] {{ flex: 1 1 220px; min-width: 160px; }}
    .checkbox {{ display: flex; align-items: center; gap: 0.35rem; font-size: 0.9rem; color: #333; }}
    .teller-regel {{ color: var(--grijs); font-size: 0.9rem; margin: 0.6rem 0 1rem; }}

    .vacature {{ background: #fff; border: 1px solid var(--rand); border-radius: 12px;
      padding: 1rem 1.1rem; margin-bottom: 0.9rem; }}
    .kop {{ display: flex; gap: 0.8rem; align-items: flex-start; }}
    .score {{ flex: none; width: 2.6rem; height: 2.6rem; border-radius: 50%;
      display: grid; place-items: center; font-weight: 700; font-size: 1rem;
      color: #fff; background: var(--kleur); }}
    .kop-tekst {{ min-width: 0; }}
    .kop h2 {{ font-size: 1.08rem; margin: 0; line-height: 1.3; }}
    .kop h2 a {{ color: var(--blauw); text-decoration: none; }}
    .kop h2 a:hover {{ text-decoration: underline; }}
    .label {{ font-size: 0.8rem; font-weight: 600; }}
    .meta {{ color: var(--grijs); font-size: 0.88rem; margin: 0.5rem 0 0; }}

    .chips {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.6rem 0 0.2rem; }}
    .chip {{ font-size: 0.8rem; background: #f0f1f4; border: 1px solid var(--rand);
      border-radius: 999px; padding: 0.15rem 0.6rem; color: #333; white-space: nowrap; }}
    .chip-profiel {{ background: #eaf2fb; border-color: #cfe0f5; color: #0b4a8a; white-space: normal; }}
    .chip-hybride {{ background: #e7f6ec; border-color: #c6ecd3; color: #1a7f37; }}

    details.match {{ margin: 0.7rem 0 0; }}
    details.match > summary {{ cursor: pointer; font-size: 0.88rem; font-weight: 600; color: #444; }}
    .match ul, .waarschuwing ul, .dealbreaker ul {{ margin: 0.4rem 0 0; padding-left: 1.2rem; font-size: 0.88rem; }}
    .waarschuwing {{ color: #9a6700; margin-top: 0.6rem; }}
    .waarschuwing strong, .dealbreaker strong {{ font-size: 0.88rem; }}
    .dealbreaker {{ color: #b3261e; margin-top: 0.6rem; }}

    .knop {{ display: inline-block; margin-top: 0.8rem; font-size: 0.88rem; font-weight: 600;
      color: var(--blauw); text-decoration: none; border: 1px solid #cfe0f5; background: #eaf2fb;
      padding: 0.35rem 0.8rem; border-radius: 8px; }}
    .knop:hover {{ background: #dceafb; }}
    .leeg {{ color: var(--grijs); }}
    footer {{ margin-top: 2rem; color: #999; font-size: 0.83rem; }}

    @media (max-width: 560px) {{
      .stats {{ grid-template-columns: repeat(2, 1fr); }}
      .filters select, .filters input[type=search] {{ flex: 1 1 100%; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Vacature Radar</h1>
    <p class="uitleg">Vacatures gematcht tegen Kevins zoekprofielen (regio Midden/Oost en
      Amsterdam). Bijgewerkt op {datum_nu}.</p>
  </header>
  {statchips}
  <main>
    {filterbalk}
    <div id="vacatures">{kaarten}</div>
  </main>
  <footer>
    <p>Gemaakt met Vacature Radar. Scores en labels zijn een hulpmiddel, geen oordeel.
    Salaris- en hybride-indicaties worden automatisch uit de vacaturetekst geschat
    en kunnen afwijken.</p>
  </footer>
  <script>
    (function () {{
      var q = document.getElementById('zoek');
      var fProfiel = document.getElementById('f-profiel');
      var fBron = document.getElementById('f-bron');
      var fHybride = document.getElementById('f-hybride');
      var fLaag = document.getElementById('f-laag');
      var fSort = document.getElementById('f-sort');
      var lijst = document.getElementById('vacatures');
      var teller = document.getElementById('teller');
      var kaarten = Array.prototype.slice.call(lijst.querySelectorAll('.vacature'));

      function pas() {{
        var term = (q.value || '').toLowerCase().trim();
        var prof = fProfiel.value, bron = fBron.value;
        var alleenHy = fHybride.checked, toonLaag = fLaag.checked;
        var zichtbaar = 0;
        kaarten.forEach(function (k) {{
          var ok = true;
          if (term && k.dataset.zoek.indexOf(term) === -1) ok = false;
          if (prof && k.dataset.profiel !== prof) ok = false;
          if (bron && k.dataset.bron !== bron) ok = false;
          if (alleenHy && k.dataset.hybride !== 'true') ok = false;
          if (!toonLaag && k.dataset.laag === '1') ok = false;
          k.style.display = ok ? '' : 'none';
          if (ok) zichtbaar++;
        }});
        teller.textContent = zichtbaar;
        var gesorteerd = kaarten.slice().sort(function (a, b) {{
          var sa = +a.dataset.score, sb = +b.dataset.score;
          var da = a.dataset.datum || '', db = b.dataset.datum || '';
          if (fSort.value === 'datum') return db.localeCompare(da) || (sb - sa);
          return (sb - sa) || db.localeCompare(da);
        }});
        gesorteerd.forEach(function (k) {{ lijst.appendChild(k); }});
      }}

      [q, fProfiel, fBron, fHybride, fLaag, fSort].forEach(function (el) {{
        el.addEventListener('input', pas);
        el.addEventListener('change', pas);
      }});
      pas();
    }})();
  </script>
</body>
</html>
"""

    os.makedirs(PUBLIC_DIR, exist_ok=True)
    uitvoer = os.path.join(PUBLIC_DIR, "index.html")
    with open(uitvoer, "w", encoding="utf-8") as f:
        f.write(pagina)

    print(f"[render] Site gebouwd: {uitvoer} "
          f"({len(top)} topmatches, {len(laag)} lage matches, {aantal_afgewezen} afgewezen).")


if __name__ == "__main__":
    main()
