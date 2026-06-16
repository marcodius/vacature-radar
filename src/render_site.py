"""Stap 3: de statische site bouwen.

Leest data/jobs_scored.json en schrijft public/index.html in eenvoudig
Nederlands, zonder JavaScript-framework. Per vacature tonen we score, label,
het gematchte zoekprofiel, matchredenen, waarschuwingen, eventuele
dealbreaker-indicatie, salaris- en hybride-indicatie, locatie en bron.

Vacatures met een harde dealbreaker staan niet in jobs_scored.json (die zitten
in data/rejected_jobs.json) en worden dus niet getoond.

Gebruik:  python src/render_site.py
"""

import datetime
import html
import json
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
PUBLIC_DIR = os.path.join(PROJECT_DIR, "public")

LABEL_KLEUR = {
    "Zeer interessant": "#1a7f37",
    "Interessant": "#0b5cad",
    "Mogelijk interessant": "#9a6700",
    "Lage match": "#6b6b6b",
}


def e(tekst):
    return html.escape(str(tekst or ""))


def hybride_tekst(waarde):
    if waarde is True:
        return "Hybride"
    if waarde is False:
        return "Volledig op kantoor"
    return "Hybride onbekend"


def vacature_html(v):
    titel = e(v.get("titel"))
    url = e(v.get("url"))
    titel_link = f"<a href='{url}' target='_blank' rel='noopener'>{titel}</a>" if url else titel

    label = v.get("label", "")
    kleur = LABEL_KLEUR.get(label, "#6b6b6b")

    meta = " &middot; ".join(filter(None, [
        e(v.get("bedrijf")), e(v.get("locatie")), e(v.get("datum")),
        f"Bron: {e(v.get('bron'))}",
    ]))

    # Kenmerken met duidelijke labels (niet aan elkaar geplakt).
    salaris = v.get("salaris_indicatie") or "niet vermeld"
    kenmerken_html = (
        "<dl class='kenmerken'>"
        f"<div><dt>Zoekprofiel:</dt><dd>{e(v.get('profiel'))}</dd></div>"
        f"<div><dt>Werkvorm:</dt><dd>{e(hybride_tekst(v.get('hybride')))}</dd></div>"
        f"<div><dt>Salaris:</dt><dd>{e(salaris)}</dd></div>"
        "</dl>"
    )

    blokken = []
    redenen = v.get("redenen", [])
    if redenen:
        items = "".join(f"<li>{e(r)}</li>" for r in redenen)
        blokken.append(f"<div class='match'><strong>Waarom deze match?</strong><ul>{items}</ul></div>")

    waarschuwingen = v.get("waarschuwingen", [])
    if waarschuwingen:
        items = "".join(f"<li>{e(w)}</li>" for w in waarschuwingen)
        blokken.append(f"<div class='waarschuwing'><strong>Let op</strong><ul>{items}</ul></div>")

    dealbreakers = v.get("dealbreakers", [])
    if dealbreakers:
        items = "".join(f"<li>{e(d)}</li>" for d in dealbreakers)
        blokken.append(f"<div class='dealbreaker'><strong>Dealbreakers</strong><ul>{items}</ul></div>")

    return f"""
    <article class="vacature">
      <div class="kop">
        <h2>{titel_link}</h2>
        <span class="label" style="background:{kleur}">{e(label)} &middot; {v.get('score', 0)}</span>
      </div>
      <p class="meta">{meta}</p>
      {kenmerken_html}
      {''.join(blokken)}
    </article>
    """


def main():
    scored_pad = os.path.join(DATA_DIR, "jobs_scored.json")
    if not os.path.exists(scored_pad):
        print("[render] data/jobs_scored.json ontbreekt. Draai eerst score_jobs.py.")
        return

    with open(scored_pad, "r", encoding="utf-8") as f:
        vacatures = json.load(f)

    # Alleen vacatures met score >= 50 worden standaard getoond.
    DREMPEL = 50
    top = [v for v in vacatures if v.get("score", 0) >= DREMPEL]
    laag = [v for v in vacatures if v.get("score", 0) < DREMPEL]

    # Tel afgewezen dealbreakers en opgehaalde (ruwe) vacatures.
    rejected_pad = os.path.join(DATA_DIR, "rejected_jobs.json")
    aantal_afgewezen = 0
    if os.path.exists(rejected_pad):
        with open(rejected_pad, "r", encoding="utf-8") as f:
            aantal_afgewezen = len(json.load(f))

    raw_pad = os.path.join(DATA_DIR, "jobs_raw.json")
    aantal_opgehaald = 0
    if os.path.exists(raw_pad):
        with open(raw_pad, "r", encoding="utf-8") as f:
            aantal_opgehaald = len(json.load(f))

    datum_nu = datetime.date.today().strftime("%d-%m-%Y")

    samenvatting_html = (
        "<div class='samenvatting'>"
        "<strong>Samenvatting</strong>"
        "<ul>"
        f"<li>Opgehaalde vacatures: {aantal_opgehaald}</li>"
        f"<li>Getoonde topmatches (score &ge; {DREMPEL}): {len(top)}</li>"
        f"<li>Afgewezen dealbreakers: {aantal_afgewezen}</li>"
        f"<li>Verborgen lage matches: {len(laag)}</li>"
        "</ul></div>"
    )

    if top:
        top_html = "".join(vacature_html(v) for v in top)
    else:
        top_html = "<p>Geen topmatches gevonden. Kijk eventueel bij de lage matches hieronder.</p>"

    if laag:
        laag_kaarten = "".join(vacature_html(v) for v in laag)
        laag_html = (
            "<details class='lage'>"
            f"<summary>Lage matches / ter controle ({len(laag)})</summary>"
            f"{laag_kaarten}"
            "</details>"
        )
    else:
        laag_html = ""

    lijst_html = (
        f"{samenvatting_html}"
        f"<h2 class='sectie'>Topmatches</h2>{top_html}"
        f"{laag_html}"
    )

    pagina = f"""<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vacature Radar</title>
  <style>
    body {{ font-family: -apple-system, Arial, sans-serif; max-width: 860px;
      margin: 0 auto; padding: 1rem; color: #1a1a1a; background: #f7f7f7; line-height: 1.5; }}
    header {{ margin-bottom: 1.5rem; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .uitleg {{ color: #555; font-size: 0.95rem; }}
    .vacature {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
      padding: 1rem 1.25rem; margin-bottom: 1rem; }}
    .kop {{ display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }}
    .kop h2 {{ font-size: 1.1rem; margin: 0; }}
    .kop h2 a {{ color: #0b5cad; text-decoration: none; }}
    .kop h2 a:hover {{ text-decoration: underline; }}
    .label {{ color: #fff; padding: 0.2rem 0.7rem; border-radius: 999px;
      font-size: 0.8rem; white-space: nowrap; font-weight: 600; }}
    .meta {{ color: #666; font-size: 0.9rem; margin: 0.4rem 0 0.6rem; }}
    .kenmerken {{ margin: 0 0 0.7rem; font-size: 0.9rem; }}
    .kenmerken div {{ display: flex; gap: 0.4rem; margin: 0.15rem 0; }}
    .kenmerken dt {{ font-weight: 600; color: #444; min-width: 90px; }}
    .kenmerken dd {{ margin: 0; color: #222; }}
    .samenvatting {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
      padding: 0.8rem 1.1rem; margin-bottom: 1.2rem; font-size: 0.92rem; }}
    .samenvatting ul {{ margin: 0.4rem 0 0; padding-left: 1.2rem; }}
    details.lage {{ margin-top: 1.5rem; }}
    details.lage > summary {{ cursor: pointer; font-weight: 600; font-size: 1rem;
      padding: 0.6rem 0; border-top: 1px solid #ddd; }}
    h2.sectie {{ font-size: 1.1rem; margin: 0.5rem 0 1rem; }}
    .match ul, .waarschuwing ul, .dealbreaker ul {{ margin: 0.3rem 0 0.6rem; padding-left: 1.2rem;
      font-size: 0.9rem; }}
    .match strong, .waarschuwing strong, .dealbreaker strong {{ font-size: 0.9rem; }}
    .waarschuwing {{ color: #9a6700; }}
    .dealbreaker {{ color: #b3261e; }}
    footer {{ margin-top: 2rem; color: #888; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <header>
    <h1>Vacature Radar</h1>
    <p class="uitleg">
      Vacatures gematcht tegen Kevins twee zoekprofielen (regio Midden/Oost en
      Amsterdam), gesorteerd op score. Bijgewerkt op {datum_nu}.
    </p>
  </header>
  <main>
    {lijst_html}
  </main>
  <footer>
    <p>Gemaakt met Vacature Radar. Scores en labels zijn een hulpmiddel, geen oordeel.
    Salaris- en hybride-indicaties worden automatisch uit de vacaturetekst geschat
    en kunnen afwijken.</p>
  </footer>
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
