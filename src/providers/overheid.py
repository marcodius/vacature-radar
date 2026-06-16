"""Provider voor overheidsvacatures (CSO Vacature API).

Bron: Carriere Sites Overheid (CSO) — alle vacatures van WerkenvoorNederland.nl,
WerkenbijdeOverheid.nl en Mobiliteitsbank.nl. De data is open (CC-0), maar de
API vereist een sleutel die je gratis aanvraagt met een account.
Documentatie: https://docs.api.cso20.net/  (endpoint: https://api.cso20.net/v1/JobAPI/)

Werkt in twee standen, net als de Nationale Vacaturebank:
  * gebruik_mock = true  -> voorbeeldvacatures zodat de pijplijn werkt.
  * gebruik_mock = false -> echte API met sleutel uit environment CSO_API_KEY.

Er wordt NOOIT gescrapet en er staan GEEN sleutels in deze code.
"""

import os

import requests

NAAM = "Overheid (CSO)"

# JSON-API: functie wordt aan het pad toegevoegd, .json-extensie is vereist.
API_URL = "https://api.cso20.net/v1/JobAPI/getJobs.json"


def _mock_vacatures():
    """Voorbeeld-overheidsvacatures zodat de pijplijn werkt zonder API-sleutel."""
    return [
        {
            "titel": "Customer Operations Specialist",
            "bedrijf": "Gemeente Utrecht",
            "locatie": "Utrecht",
            "url": "https://www.werkenvoornederland.nl/vacature/voorbeeld-1",
            "omschrijving": (
                "Je verbetert klantprocessen, beheert het CRM en maakt rapportages "
                "voor onze dienstverlening. Hybride werken mogelijk. "
                "Schaal 9, circa € 3.500 bruto per maand."
            ),
            "datum": "2026-06-15",
        },
        {
            "titel": "Projectcoördinator Digitalisering",
            "bedrijf": "Provincie Gelderland",
            "locatie": "Arnhem",
            "url": "https://www.werkenvoornederland.nl/vacature/voorbeeld-2",
            "omschrijving": (
                "Je ondersteunt projecten rond procesoptimalisatie en automatisering. "
                "Hybride werken. Salaris circa € 3.700 per maand."
            ),
            "datum": "2026-06-14",
        },
    ]


def _normaliseer(item):
    return {
        "titel": item.get("titel") or item.get("title") or "Onbekende functie",
        "bedrijf": item.get("organisatie") or item.get("bedrijf") or item.get("company") or "Overheid",
        "locatie": item.get("locatie") or item.get("standplaats") or item.get("location") or "Onbekend",
        "url": item.get("url") or item.get("link") or "",
        "omschrijving": item.get("omschrijving") or item.get("description") or "",
        "datum": item.get("datum") or item.get("publicatiedatum") or item.get("date") or "",
        "bron": NAAM,
    }


def fetch(config):
    """Haal vacatures op. config is het 'overheid'-blok uit sources.json."""
    max_resultaten = config.get("max_resultaten", 50)

    if config.get("gebruik_mock", True):
        items = _mock_vacatures()
        return [_normaliseer(i) for i in items][:max_resultaten]

    api_key = os.environ.get("CSO_API_KEY")
    if not api_key:
        print(
            "[Overheid] Geen CSO_API_KEY gevonden in environment. "
            "Val terug op mock-data. Zet de sleutel of zet gebruik_mock op true."
        )
        items = _mock_vacatures()
        return [_normaliseer(i) for i in items][:max_resultaten]

    try:
        # De CSO JSON-API verwacht POST met de sleutel; pas zo nodig aan op de
        # echte documentatie (https://docs.api.cso20.net/).
        response = requests.post(
            API_URL,
            json={"apiKey": api_key, "limit": max_resultaten},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("vacatures") or data.get("jobs") or data.get("results") or []
        return [_normaliseer(i) for i in items][:max_resultaten]
    except Exception as fout:  # noqa: BLE001
        print(f"[Overheid] Ophalen mislukt: {fout}. Val terug op mock-data.")
        items = _mock_vacatures()
        return [_normaliseer(i) for i in items][:max_resultaten]
