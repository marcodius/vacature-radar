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

    # Pillen: profiel, hybride, salaris.
    pillen = [f"<span class='pil profiel'>{e(v.get('profiel'))}</span>"]
    pillen.append(f"<span class='pil'>{e(hybride_tekst(v.get('hybride')))}</span>")
    if v.get("salaris_indicatie"):
        pillen.append(f"<span class='pil'>{e(v.get('salaris_indicatie'))}</span>")
    pillen_html = "".join(pillen)

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
      <div class="pillen">{pillen_html}</div>
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

    # Tel afgewezen vacatures voor een korte vermelding.
    rejected_pad = os.path.join(DATA_DIR, "rejected_jobs.json")
    aantal_afgewezen = 0
    if os.path.exists(rejected_pad):
        with open(rejected_pad, "r", encoding="utf-8") as f:
            aantal_afgewezen = len(json.load(f))

    datum_nu = datetime.date.today().strftime("%d-%m-%Y")

    if vacatures:
        lijst_html = "".join(vacature_html(v) for v in vacatures)
    else:
        lijst_html = "<p>Geen vacatures gevonden die aan het profiel voldoen.</p>"

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
    .pillen {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.6rem; }}
    .pil {{ background: #eef1f5; color: #333; border-radius: 6px; padding: 0.15rem 0.55rem;
      font-size: 0.8rem; }}
    .pil.profiel {{ background: #dde7f3; color: #0b3c6b; }}
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
      {len(vacatures)} getoond, {aantal_afgewezen} afgewezen op een dealbreaker.
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

    print(f"[render] Site gebouwd: {uitvoer} ({len(vacatures)} vacatures getoond).")


if __name__ == "__main__":
    main()
