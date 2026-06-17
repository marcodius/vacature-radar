"""Snel checken of een werkgever via een publiek ATS te ontsluiten is.

Probeert de vier ondersteunde ATS-platforms (greenhouse, recruitee, lever,
smartrecruiters) voor een opgegeven 'board' en laat zien hoeveel vacatures er
zijn — en, als er een profiel is, hoeveel daarvan relevant zijn en getoond
zouden worden voor Kevin. Zo bepaal je in één minuut of een bedrijf de moeite
waard is om aan config/sources.json ('ats_bedrijven' -> 'werkgevers') toe te
voegen.

Gebruik:
  python tools/check_werkgever.py <board> [<board> ...]

'board' is de identifier in de ATS-URL van het bedrijf, meestal de bedrijfsnaam
in kleine letters (bijv. 'adyen', 'channable', 'bunq'). Vind je een hit, voeg dan
toe:  {"naam": "Bedrijf", "platform": "<platform>", "board": "<board>"}
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def _jget(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Chrome/126",
                                               "Accept": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=12))


def _aantallen(board):
    """Geef {platform: aantal} voor de platforms die vacatures teruggeven."""
    checks = {
        "greenhouse": lambda b: len(_jget(f"https://boards-api.greenhouse.io/v1/boards/{b}/jobs").get("jobs") or []),
        "recruitee": lambda b: len(_jget(f"https://{b}.recruitee.com/api/offers/").get("offers") or []),
        "lever": lambda b: len(_jget(f"https://api.lever.co/v0/postings/{b}?mode=json")),
        "smartrecruiters": lambda b: _jget(f"https://api.smartrecruiters.com/v1/companies/{b}/postings").get("totalFound", 0),
    }
    gevonden = {}
    for platform, fn in checks.items():
        try:
            n = fn(board)
            if n:
                gevonden[platform] = n
        except Exception:  # noqa: BLE001
            pass
    return gevonden


def _yield(platform, board):
    """Hoeveel vacatures zijn relevant en zouden getoond worden voor Kevin?"""
    try:
        from providers import ats, relevance
        import score_jobs as score
    except Exception as fout:  # noqa: BLE001
        return None, f"(profiel/score niet beschikbaar: {fout})"
    try:
        profiel, _ = score.laad_profiel()
    except Exception:  # noqa: BLE001
        return None, "(geen profiel gevonden)"
    rijen = ats.PLATFORMS[platform](board, board, 150)
    getoond = []
    for v in rijen:
        if not relevance.is_relevant(v["titel"], v.get("omschrijving", "")):
            continue
        r = score.score_uitgebreid(dict(v), profiel)
        if not (r["hard_dealbreaker"] or r["score_ruw"] < 0):
            getoond.append((r["score"], v["titel"], v["locatie"]))
    getoond.sort(reverse=True)
    return getoond, None


def main(boards):
    if not boards:
        print(__doc__)
        return
    for board in boards:
        print(f"\n=== {board} ===")
        gevonden = _aantallen(board)
        if not gevonden:
            print("  geen publiek ATS gevonden (probeer een andere board-naam).")
            continue
        for platform, n in gevonden.items():
            getoond, fout = _yield(platform, board)
            if fout:
                print(f"  {platform}: {n} vacatures {fout}")
            else:
                print(f"  {platform}: {n} vacatures, {len(getoond)} relevant+getoond voor Kevin")
                for sc, titel, loc in getoond[:5]:
                    print(f"      {sc:3d}  {titel[:40]:40} | {loc[:24]}")
        beste = max(gevonden, key=gevonden.get)
        print(f"  -> toevoegen: {{\"naam\": \"{board.capitalize()}\", \"platform\": \"{beste}\", \"board\": \"{board}\"}}")


if __name__ == "__main__":
    main(sys.argv[1:])
