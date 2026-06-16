"""Stap 2: vacatures lokaal scoren op relevantie.

Twee scoremodellen:

1. Eenvoudig profiel (config/profile.json met 'trefwoorden' / 'locaties').
2. Uitgebreid profiel met zoekprofielen (config/profile.kevin.json met 'profiles').
   Dit model past harde filters, titel-, inhoud- en contextmatch toe, kent
   labels en waarschuwingen toe, en wijst per vacature een zoekprofiel aan.

Volgorde van het uitgebreide model:
  1. Harde filters: hybride, salaris, dealbreakers.
  2. Titelmatch: prioriteit 1 of 2.
  3. Inhoudelijke match: CRM, operations, procesoptimalisatie.
  4. Context: locatie, OV, SaaS/tech/cultuur.
  5. Sorteren en publiceren.

Vacatures met een harde dealbreaker (of negatieve score) gaan naar
data/rejected_jobs.json en worden niet op de publieke site getoond.
Goede matches gaan naar data/jobs_scored.json.

Gebruik:  python3 src/score_jobs.py
"""

import json
import os
import re

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
DATA_DIR = os.path.join(PROJECT_DIR, "data")

# Welke profielfiles proberen we, in volgorde?
PROFIEL_KANDIDATEN = ["profile.json", "profile.kevin.json"]


# --------------------------------------------------------------------------
# Config laden
# --------------------------------------------------------------------------

def laad_profiel():
    """Laad het eerste bestaande profiel; val terug op .example-bestanden."""
    for naam in PROFIEL_KANDIDATEN:
        pad = os.path.join(CONFIG_DIR, naam)
        if os.path.exists(pad):
            with open(pad, "r", encoding="utf-8") as f:
                return json.load(f), naam
    # Geen echte config: gebruik de Kevin-example als die er is, anders simpel.
    for naam in ["profile.kevin.example.json", "profile.example.json"]:
        pad = os.path.join(CONFIG_DIR, naam)
        if os.path.exists(pad):
            print(f"[score] Geen eigen profiel gevonden, gebruik {naam}.")
            with open(pad, "r", encoding="utf-8") as f:
                return json.load(f), naam
    raise FileNotFoundError("Geen profielbestand gevonden in config/.")


# --------------------------------------------------------------------------
# Hulpfuncties voor detectie
# --------------------------------------------------------------------------

HYBRIDE_POSITIEF = [
    "hybride", "hybrid", "deels thuis", "thuiswerk", "thuiswerken",
    "vanuit huis", "remote", "op afstand werken",
]
HYBRIDE_GEEN = [
    "volledig op kantoor", "fulltime op kantoor", "100% op kantoor",
    "geen thuiswerk", "niet thuiswerken", "alleen op kantoor",
    "geen hybride", "geen mogelijkheid tot thuiswerken",
]

CRM_TOOLS = ["crm", "salesforce", "hubspot"]
PROCES_TERMEN = [
    "procesoptimalisatie", "procesverbetering", "automatisering",
    "automatiseringen", "rapportage", "rapportages", "data-analyse",
    "dataanalyse", "klantproces", "klantprocessen",
]
TECH_TERMEN = ["saas", "scale-up", "scaleup", "tech", "startup", "software", "platform"]
FORMEEL_TERMEN = ["zeer formele", "hiërarchische", "hierarchische", "corporate", "pak-en-stropdas"]
SLECHT_OV_TERMEN = ["bedrijventerrein", "industrieterrein", "slecht bereikbaar", "alleen met auto"]

# Locaties die expliciet buiten Nederland vallen en moeten worden afgewezen.
# (Let op: "Nederland, TX" is een Amerikaanse plaats; de TX/Texas-tokens vangen die af.)
BUITENLAND_LOCATIES = [
    "tx", "texas", "beaumont", "groves", "usa", "u.s.", "united states",
    "verenigde staten", "canada", "india", "uk", "united kingdom", "spain",
    "spanje", "germany", "duitsland", "france", "frankrijk", "belgium",
]
NL_LOCATIES = ["netherlands", "nederland", "holland"]
# Compacte lijst NL-steden/provincies om 'wel in Nederland' te herkennen
# (los van Kevins zoekgebieden). Niet uitputtend; alleen voor de locatieklasse.
NL_STEDEN = [
    "rotterdam", "den haag", "the hague", "eindhoven", "groningen", "tilburg",
    "almere", "breda", "haarlem", "zwolle", "leiden", "maastricht", "delft",
    "apeldoorn", "enschede", "deventer", "hilversum", "amstelveen", "hoofddorp",
    "zaandam", "dordrecht", "leeuwarden", "den bosch", "'s-hertogenbosch",
    "noord-holland", "zuid-holland", "gelderland", "utrecht", "brabant",
    "noord-brabant", "overijssel", "flevoland", "friesland", "limburg", "drenthe",
    "zeeland",
]
EU_TERMEN = ["europe", "europa", " eu "]
REMOTE_TERMEN = ["remote", "thuiswerk", "vanuit huis", "op afstand", "anywhere"]


def _woord_in(term, *teksten):
    patroon = r"\b" + re.escape(term.lower()) + r"\b"
    return any(re.search(patroon, t) for t in teksten)


def classificeer_locatie(locatie, tekst, gematchte_locatie, land=""):
    """Bepaal de locatieklasse:
    'zoekgebied' (Nederlandse stad uit een profiel),
    'remote_eu' (expliciet remote Nederland/Europa),
    'nl' (Nederland maar buiten de zoekgebieden),
    'buiten' (buitenland of niet herleidbaar -> dealbreaker).

    'land' is een bronhint (bijv. "NL" voor Nederlandse API/sitemap-bronnen):
    een vacature uit een NL-bron waarvan de plaats niet uit de tekst te halen is,
    wordt als 'nl' gezien i.p.v. onterecht als buitenland.
    """
    loc = (locatie or "").lower()

    # 1. Expliciet buitenland -> afwijzen (vangt ook 'Nederland, TX' via tx/texas).
    for t in BUITENLAND_LOCATIES:
        if _woord_in(t, loc) or _woord_in(t, tekst):
            return "buiten"

    # 2. Stad uit een zoekprofiel.
    if gematchte_locatie:
        return "zoekgebied"

    # 3. Expliciet remote in Nederland of Europa (ook geldig voor NL-bronnen).
    is_remote = any(r in loc for r in REMOTE_TERMEN) or any(r in tekst for r in REMOTE_TERMEN)
    nl_of_eu = (any(n in loc for n in NL_LOCATIES) or any(n in tekst for n in NL_LOCATIES)
                or any(eu in loc for eu in EU_TERMEN) or any(eu in tekst for eu in EU_TERMEN)
                or land.upper() == "NL")
    if is_remote and nl_of_eu:
        return "remote_eu"

    # 4. Nederland, maar buiten de twee zoekgebieden.
    if (any(n in loc for n in NL_LOCATIES) or _woord_in("nl", loc)
            or any(_woord_in(s, loc) for s in NL_STEDEN)
            or land.upper() == "NL"):
        return "nl"

    # 5. Niet herleidbaar tot Nederland -> afwijzen.
    return "buiten"

# Dealbreakers: (lijst triggers, label, straf, hard?)
DEALBREAKERS = [
    (["callcenter", "call center", "call-center"], "Callcenter", -60, True),
    (["hele dag telefonie", "hele dag bellen", "telefonische verkoop"], "Hele dag telefonie", -60, True),
    (["koude acquisitie", "cold calling", "cold-calling", "outbound bellen"], "Koude acquisitie", -60, True),
    (["harde sales targets", "new business target", "omzetverantwoordelijkheid",
      "salestargets", "sales targets"], "Harde sales targets", -50, True),
]


def _bevat(tekst, termen):
    return [t for t in termen if t in tekst]


def _bevat_woord(tekst, term):
    """Match een term op woordgrenzen, zodat 'Ede' niet matcht in 'bredere'."""
    return re.search(r"\b" + re.escape(term.lower()) + r"\b", tekst) is not None


def detecteer_hybride(tekst):
    """Geeft True (hybride), False (expliciet geen) of None (niet vermeld)."""
    if _bevat(tekst, HYBRIDE_GEEN):
        return False
    if _bevat(tekst, HYBRIDE_POSITIEF):
        return True
    return None


def extraheer_maandsalaris(tekst):
    """Schat het bruto maandsalaris (40u) uit de tekst. None als niet gevonden.

    Heuristiek: bedragen tussen 1500-9000 worden als maand gezien, 18000-150000
    als jaar (gedeeld door 12). Het hoogst gevonden bedrag telt.
    """
    # Vind getallen met optionele duizend-punt/komma, eventueel met 'k'.
    kandidaten = []
    for match in re.finditer(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{3})+|\d{2,6})(\s*k\b)?", tekst):
        ruw = match.group(1).replace(".", "").replace(",", "")
        try:
            waarde = int(ruw)
        except ValueError:
            continue
        if match.group(2):  # 'k' achtervoegsel, bijv. 55k
            waarde *= 1000
        kandidaten.append(waarde)

    maandbedragen = []
    for waarde in kandidaten:
        if 1500 <= waarde <= 9000:
            maandbedragen.append(waarde)
        elif 18000 <= waarde <= 200000:
            maandbedragen.append(round(waarde / 12))
    if not maandbedragen:
        return None
    return max(maandbedragen)


def titel_match(titel, titels):
    """Geeft de gematchte titel terug, of None. Case-insensitief, deelmatch."""
    t = titel.lower()
    for kandidaat in titels:
        if kandidaat.lower() in t:
            return kandidaat
    return None


def kies_profiel(tekst, profielen):
    """Wijs het zoekprofiel toe op basis van locatie. Geeft (profiel, gematchte_locatie)."""
    for profiel in profielen:
        for locatie in profiel.get("locations", []):
            if _bevat_woord(tekst, locatie):
                return profiel, locatie
    return None, None


# --------------------------------------------------------------------------
# Uitgebreid scoremodel
# --------------------------------------------------------------------------

def score_uitgebreid(vacature, profiel_config):
    tekst = " ".join([
        vacature.get("titel", ""), vacature.get("bedrijf", ""),
        vacature.get("locatie", ""), vacature.get("omschrijving", ""),
    ]).lower()
    titel = vacature.get("titel", "")

    score = 0
    redenen = []
    waarschuwingen = []
    dealbreakers = []
    hard_dealbreaker = False

    salary = profiel_config.get("salary", {})
    min_salaris = salary.get("minimum_monthly_gross_40h", 0)
    voorkeur_min = salary.get("preferred_monthly_gross_40h_min", 0)
    profielen = profiel_config.get("profiles", [])

    # --- Profiel + locatie ---
    # Match het zoekgebied bij voorkeur op het expliciete locatieveld (+ titel),
    # niet op de hele omschrijving: een vacature in Hengelo die Utrecht terloops
    # noemt, hoort niet als 'Utrecht' te tellen. Alleen als het locatieveld
    # generiek is ("Nederland"/"Onbekend"/"Remote") vallen we terug op de tekst.
    loc_veld = (vacature.get("locatie", "") or "").strip().lower()
    generiek = loc_veld in ("", "nederland", "the netherlands", "holland",
                            "onbekend", "remote", "thuis", "hybride")
    locatie_tekst = tekst if generiek else " ".join(
        [vacature.get("locatie", ""), titel]
    ).lower()
    profiel, gematchte_locatie = kies_profiel(locatie_tekst, profielen)
    loc_klasse = classificeer_locatie(
        vacature.get("locatie", ""), tekst, gematchte_locatie,
        land=vacature.get("land", ""),
    )
    if profiel:
        profiel_naam = profiel["name"]
    elif loc_klasse == "remote_eu":
        profiel_naam = "Remote (Nederland/Europa)"
    elif loc_klasse == "nl":
        profiel_naam = "Nederland (buiten zoekgebied)"
    else:
        profiel_naam = "Buiten zoekgebied"

    # --- Stap 1: harde filters ---
    hybride = detecteer_hybride(tekst)
    if hybride is False:
        dealbreakers.append("Geen hybride werk (volledig op kantoor)")
        score -= 100
        hard_dealbreaker = True
    elif hybride is True:
        score += 15
        redenen.append("Hybride werken expliciet genoemd (+15)")
    else:
        waarschuwingen.append("Hybride werken niet vermeld in de vacature")

    salaris_maand = extraheer_maandsalaris(vacature.get("omschrijving", ""))
    salaris_indicatie = None
    if salaris_maand is not None:
        bedrag = f"{salaris_maand:,}".replace(",", ".")
        salaris_indicatie = f"± € {bedrag} bruto p/m (40u, geschat)"
        if salaris_maand < min_salaris:
            dealbreakers.append(f"Salaris onder € {min_salaris} ({salaris_indicatie})")
            score -= 80
            hard_dealbreaker = True
        elif salaris_maand >= voorkeur_min:
            score += 5
            redenen.append(f"Salaris boven voorkeursminimum (+5): {salaris_indicatie}")
    else:
        waarschuwingen.append("Salaris niet (duidelijk) vermeld")

    for triggers, label, straf, hard in DEALBREAKERS:
        if _bevat(tekst, triggers):
            dealbreakers.append(label)
            score += straf
            if hard:
                hard_dealbreaker = True

    # "Vrijwel uitsluitend administratie": alleen straffen als geen operations-context.
    admin_only = ("uitsluitend administratie" in tekst or "alleen administratie" in tekst
                  or ("administratief medewerker" in titel.lower()
                      and not _bevat(tekst, ["operations", "crm", "klantproces", "orderverwerking",
                                             "sales support", "bredere"])))
    if admin_only:
        dealbreakers.append("Functie lijkt vrijwel uitsluitend administratie")
        score -= 40
        hard_dealbreaker = True

    # --- Stap 2: titelmatch (gebruik gematcht profiel, anders alle titels) ---
    if profiel:
        p1 = profiel.get("priority_1_titles", [])
        p2 = profiel.get("priority_2_titles", [])
    else:
        p1 = [t for pr in profielen for t in pr.get("priority_1_titles", [])]
        p2 = [t for pr in profielen for t in pr.get("priority_2_titles", [])]

    m1 = titel_match(titel, p1)
    m2 = titel_match(titel, p2)
    if m1:
        score += 35
        redenen.append(f"Titel matcht prioriteit 1: '{m1}' (+35)")
    elif m2:
        score += 25
        redenen.append(f"Titel matcht prioriteit 2: '{m2}' (+25)")

    # Nuance: Commercieel Medewerker Binnendienst.
    if "commercieel medewerker binnendienst" in titel.lower():
        goed = _bevat(tekst, ["support", "crm", "klantproces", "orderverwerking",
                              "sales support", "operations", "administratie binnen"])
        slecht = _bevat(tekst, ["koude acquisitie", "targets", "outbound bellen",
                                "telefonische verkoop", "leads opvolgen", "leads opvolg"])
        if slecht:
            score -= 30
            waarschuwingen.append("Commercieel binnendienst met salesdruk/telefonie")
        elif goed:
            redenen.append("Commercieel binnendienst met support/operations-focus")

    # --- Stap 3: inhoudelijke match ---
    activiteiten = profiel_config.get("positive_work_activities", [])
    activiteit_hits = [a for a in activiteiten if a.lower().split()[0] in tekst]
    if activiteit_hits:
        score += 20
        redenen.append("Werkzaamheden passen goed (+20)")

    if _bevat(tekst, CRM_TOOLS):
        score += 10
        redenen.append("CRM / Salesforce / HubSpot genoemd (+10)")
    if _bevat(tekst, PROCES_TERMEN):
        score += 10
        redenen.append("Procesoptimalisatie / automatisering / rapportage (+10)")

    # --- Stap 4: context ---
    if loc_klasse == "zoekgebied":
        score += 15
        redenen.append(f"Locatie past: {gematchte_locatie} (+15)")
    elif loc_klasse == "remote_eu":
        redenen.append("Remote in Nederland/Europa")
    elif loc_klasse == "nl":
        dealbreakers.append("In Nederland, maar buiten de zoekgebieden (regio Midden/Oost of Amsterdam)")
        score -= 100
        hard_dealbreaker = True
    else:  # buitenland of niet herleidbaar tot Nederland -> dealbreaker
        dealbreakers.append("Locatie buiten Nederland")
        score -= 100
        hard_dealbreaker = True

    if _bevat(tekst, TECH_TERMEN):
        score += 10
        redenen.append("SaaS / tech / scale-up / moderne dienstverlener (+10)")

    if _bevat(tekst, FORMEEL_TERMEN):
        score -= 20
        waarschuwingen.append("Zeer formele / corporate cultuur (-20)")

    # OV-bereikbaarheid (vooral relevant voor Amsterdam-profiel).
    if _bevat(tekst, SLECHT_OV_TERMEN):
        score -= 25
        waarschuwingen.append("Mogelijk slecht bereikbaar met OV (-25)")

    # Label bepalen (op basis van score, begrensd 0..100 voor weergave).
    weergave_score = max(0, min(100, score))
    if hard_dealbreaker or score < 0:
        label = "Afgewezen (dealbreaker)"
    elif score >= 80:
        label = "Zeer interessant"
    elif score >= 65:
        label = "Interessant"
    elif score >= 50:
        label = "Mogelijk interessant"
    else:
        label = "Lage match"

    vacature.update({
        "score": weergave_score,
        "score_ruw": score,
        "label": label,
        "profiel": profiel_naam,
        "redenen": redenen,
        "waarschuwingen": waarschuwingen,
        "dealbreakers": dealbreakers,
        "hard_dealbreaker": hard_dealbreaker,
        "salaris_indicatie": salaris_indicatie,
        "hybride": hybride,
    })
    return vacature


# --------------------------------------------------------------------------
# Eenvoudig scoremodel (oud profiel)
# --------------------------------------------------------------------------

def score_eenvoudig(vacature, profiel):
    tekst = " ".join([
        vacature.get("titel", ""), vacature.get("bedrijf", ""),
        vacature.get("locatie", ""), vacature.get("omschrijving", ""),
    ]).lower()
    titel = vacature.get("titel", "").lower()
    score = 0
    redenen = []
    for trefwoord in profiel.get("trefwoorden", []):
        tw = trefwoord.lower()
        if tw and tw in titel:
            score += 2
            redenen.append(f"Trefwoord in titel: '{trefwoord}'")
        elif tw and tw in tekst:
            score += 1
            redenen.append(f"Trefwoord gevonden: '{trefwoord}'")
    for locatie in profiel.get("locaties", []):
        if locatie.lower() in tekst:
            score += 2
            redenen.append(f"Locatie past: '{locatie}'")
    for woord in profiel.get("uitsluiten", []):
        if woord.lower() in tekst:
            score -= 5
            redenen.append(f"Uitsluitwoord aanwezig: '{woord}' (-5)")
    vacature.update({
        "score": score, "label": "", "profiel": "",
        "redenen": redenen, "waarschuwingen": [], "dealbreakers": [],
        "hard_dealbreaker": False, "salaris_indicatie": None, "hybride": None,
    })
    return vacature


# --------------------------------------------------------------------------
# Hoofdprogramma
# --------------------------------------------------------------------------

def main():
    raw_pad = os.path.join(DATA_DIR, "jobs_raw.json")
    if not os.path.exists(raw_pad):
        print("[score] data/jobs_raw.json ontbreekt. Draai eerst fetch_jobs.py.")
        return

    with open(raw_pad, "r", encoding="utf-8") as f:
        vacatures = json.load(f)

    profiel, bron = laad_profiel()
    uitgebreid = "profiles" in profiel
    print(f"[score] Profiel: {bron} ({'uitgebreid' if uitgebreid else 'eenvoudig'} model).")

    getoond = []
    afgewezen = []
    for vacature in vacatures:
        if uitgebreid:
            v = score_uitgebreid(vacature, profiel)
            if v["hard_dealbreaker"] or v["score_ruw"] < 0:
                afgewezen.append(v)
            else:
                getoond.append(v)
        else:
            v = score_eenvoudig(vacature, profiel)
            min_score = profiel.get("min_score", 0)
            if v["score"] >= min_score:
                getoond.append(v)
            else:
                afgewezen.append(v)

    getoond.sort(key=lambda v: v["score"], reverse=True)
    afgewezen.sort(key=lambda v: v.get("score_ruw", v.get("score", 0)), reverse=True)

    with open(os.path.join(DATA_DIR, "jobs_scored.json"), "w", encoding="utf-8") as f:
        json.dump(getoond, f, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA_DIR, "rejected_jobs.json"), "w", encoding="utf-8") as f:
        json.dump(afgewezen, f, ensure_ascii=False, indent=2)

    print(f"[score] {len(getoond)} getoond, {len(afgewezen)} afgewezen "
          f"(zie data/rejected_jobs.json).")


if __name__ == "__main__":
    main()
