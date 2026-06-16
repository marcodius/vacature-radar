"""Provider voor de Nationale Vacaturebank.

De Nationale Vacaturebank heeft geen gratis, openbare API: officiele toegang
loopt via een API-sleutel die je met een account aanvraagt (zie README).
Daarom werkt deze provider in twee standen:

  * gebruik_mock = true  -> levert voorbeeldvacatures zodat de pijplijn werkt.
  * gebruik_mock = false -> roept de echte API aan met een sleutel uit de
                            environment variable NVB_API_KEY.

Er wordt NOOIT gescrapet en er staan GEEN sleutels in deze code.
"""

import os

import requests

NAAM = "Nationale Vacaturebank"

# Pas dit aan naar het echte endpoint zodra je toegang hebt.
API_URL = "https://api.nationalevacaturebank.nl/v1/vacatures"


def _mock_vacatures():
    """Voorbeeldvacatures zodat de rest van de pijplijn werkt zonder API.

    Deze set is bewust gevarieerd om het scoremodel te demonstreren:
    goede matches, een paar dealbreakers en een twijfelgeval.
    """
    return [
        {
            "titel": "CRM Operations Specialist",
            "bedrijf": "GroenSaaS",
            "locatie": "Utrecht",
            "url": "https://www.nationalevacaturebank.nl/vacature/voorbeeld-1",
            "omschrijving": (
                "Bij onze scale-up beheer je het CRM (Salesforce) en werk je aan "
                "procesoptimalisatie en automatiseringen. Informele, pragmatische "
                "cultuur met ruimte voor eigen initiatief. Hybride werken (2 dagen "
                "thuis). Salaris € 3.800 - € 4.200 bruto per maand."
            ),
            "datum": "2026-06-15",
        },
        {
            "titel": "Operations Specialist",
            "bedrijf": "TechFlow B.V.",
            "locatie": "Amersfoort",
            "url": "https://www.nationalevacaturebank.nl/vacature/voorbeeld-2",
            "omschrijving": (
                "SaaS-bedrijf zoekt operations specialist. Je verbetert klantprocessen, "
                "maakt rapportages en data-analyses, en ondersteunt projecten. Moderne "
                "organisatie, hybride werken mogelijk. € 4.000 per maand."
            ),
            "datum": "2026-06-14",
        },
        {
            "titel": "Salesforce Administrator",
            "bedrijf": "FinScale",
            "locatie": "Amsterdam Zuid",
            "url": "https://www.nationalevacaturebank.nl/vacature/voorbeeld-3",
            "omschrijving": (
                "Beheer en optimaliseer onze Salesforce-omgeving. Goed bereikbaar, "
                "naast NS-station Amsterdam Zuid. Hybride werken. Tech scale-up, "
                "informele sfeer. Salaris € 3.600 bruto per maand."
            ),
            "datum": "2026-06-13",
        },
        {
            "titel": "Customer Success Specialist",
            "bedrijf": "HelpdeskPro",
            "locatie": "Arnhem",
            "url": "https://www.nationalevacaturebank.nl/vacature/voorbeeld-4",
            "omschrijving": (
                "Je helpt klanten succesvol te worden met ons platform, beheert het "
                "CRM en verbetert klantprocessen. Hybride werken. € 3.400 per maand."
            ),
            "datum": "2026-06-12",
        },
        {
            "titel": "Medewerker Callcenter Klantenservice",
            "bedrijf": "BelBedrijf",
            "locatie": "Nijmegen",
            "url": "https://www.nationalevacaturebank.nl/vacature/voorbeeld-5",
            "omschrijving": (
                "In ons callcenter sta je de hele dag aan de telefoon. Hele dag "
                "telefonie en het actief opvolgen van leads. Volledig op kantoor."
            ),
            "datum": "2026-06-11",
        },
        {
            "titel": "Administratief Medewerker",
            "bedrijf": "Kantoor Klassiek",
            "locatie": "Ede",
            "url": "https://www.nationalevacaturebank.nl/vacature/voorbeeld-6",
            "omschrijving": (
                "Administratieve functie op een formele, hiërarchische afdeling. "
                "Vrijwel uitsluitend administratie. Volledig op kantoor, geen thuiswerk."
            ),
            "datum": "2026-06-10",
        },
        {
            "titel": "Commercieel Medewerker Binnendienst",
            "bedrijf": "VerkoopMax",
            "locatie": "Arnhem",
            "url": "https://www.nationalevacaturebank.nl/vacature/voorbeeld-7",
            "omschrijving": (
                "Je doet koude acquisitie, outbound bellen en het opvolgen van leads "
                "met harde sales targets. Omzetverantwoordelijkheid."
            ),
            "datum": "2026-06-09",
        },
        {
            "titel": "Commercieel Medewerker Binnendienst",
            "bedrijf": "ServiceSoft",
            "locatie": "Utrecht",
            "url": "https://www.nationalevacaturebank.nl/vacature/voorbeeld-8",
            "omschrijving": (
                "Sales support en orderverwerking binnen een bredere operationsrol. "
                "Je beheert het CRM en verbetert klantprocessen. Hybride werken, "
                "informele cultuur. € 3.500 per maand."
            ),
            "datum": "2026-06-08",
        },
    ]


def _normaliseer(item):
    """Zet een ruw API-item om naar het standaard vacatureformaat."""
    return {
        "titel": item.get("titel") or item.get("title") or "Onbekende functie",
        "bedrijf": item.get("bedrijf") or item.get("company") or "Onbekend bedrijf",
        "locatie": item.get("locatie") or item.get("location") or "Onbekend",
        "url": item.get("url") or item.get("link") or "",
        "omschrijving": item.get("omschrijving") or item.get("description") or "",
        "datum": item.get("datum") or item.get("date") or "",
        "bron": NAAM,
    }


def fetch(config):
    """Haal vacatures op. config is het 'nationale_vacaturebank'-blok uit sources.json."""
    max_resultaten = config.get("max_resultaten", 50)

    if config.get("gebruik_mock", True):
        items = _mock_vacatures()
        return [_normaliseer(i) for i in items][:max_resultaten]

    api_key = os.environ.get("NVB_API_KEY")
    if not api_key:
        print(
            "[Nationale Vacaturebank] Geen NVB_API_KEY gevonden in environment. "
            "Val terug op mock-data. Zet de sleutel of zet gebruik_mock op true."
        )
        items = _mock_vacatures()
        return [_normaliseer(i) for i in items][:max_resultaten]

    try:
        response = requests.get(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"limit": max_resultaten},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        # Pas de sleutel aan de echte response-structuur aan zodra bekend.
        items = data.get("vacatures") or data.get("results") or []
        return [_normaliseer(i) for i in items][:max_resultaten]
    except Exception as fout:  # noqa: BLE001 - bewust breed in versie 1
        print(f"[Nationale Vacaturebank] Ophalen mislukt: {fout}. Val terug op mock-data.")
        items = _mock_vacatures()
        return [_normaliseer(i) for i in items][:max_resultaten]
