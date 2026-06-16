"""Stap 1: vacatures ophalen uit alle ingeschakelde bronnen.

Leest config/sources.json (of het example-bestand) volgens dit schema:

    {
      "sources": {
        "<bronsleutel>": {
          "enabled": true/false,
          "type": "api" | "polite_scrape" | "manual",
          "priority": <int>,
          ... bron-specifieke opties ...
        }
      }
    }

Bronnen worden in volgorde van 'priority' opgehaald via de provider_registry en
samengevoegd in data/jobs_raw.json.

Gebruik:  python src/fetch_jobs.py
"""

import json
import os

from providers.provider_registry import get_provider

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
DATA_DIR = os.path.join(PROJECT_DIR, "data")


def laad_config(naam):
    pad = os.path.join(CONFIG_DIR, naam)
    example = os.path.join(CONFIG_DIR, naam.replace(".json", ".example.json"))
    if not os.path.exists(pad) and os.path.exists(example):
        print(f"[fetch] {naam} niet gevonden, gebruik {os.path.basename(example)}.")
        pad = example
    with open(pad, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    config = laad_config("sources.json")
    sources = config.get("sources", config)  # ondersteun ook plat schema

    # Sorteer op priority (lager = eerst).
    gesorteerd = sorted(
        sources.items(), key=lambda kv: kv[1].get("priority", 999)
    )

    alle_vacatures = []
    for bron_key, bron_config in gesorteerd:
        if not bron_config.get("enabled", False):
            print(f"[fetch] Bron '{bron_key}' staat uit, overslaan.")
            continue
        provider = get_provider(bron_key)
        if provider is None:
            print(f"[fetch] Geen provider voor '{bron_key}', overslaan.")
            continue
        print(f"[fetch] Ophalen uit '{bron_key}' (type {bron_config.get('type', '?')})...")
        # Geef de bronsleutel mee (manual-providers gebruiken die om te filteren).
        vacatures = provider.fetch({**bron_config, "_key": bron_key})
        print(f"[fetch] {len(vacatures)} vacatures uit '{bron_key}'.")
        alle_vacatures.extend(vacatures)

    os.makedirs(DATA_DIR, exist_ok=True)
    uitvoer = os.path.join(DATA_DIR, "jobs_raw.json")
    with open(uitvoer, "w", encoding="utf-8") as f:
        json.dump(alle_vacatures, f, ensure_ascii=False, indent=2)

    print(f"[fetch] Totaal {len(alle_vacatures)} vacatures opgeslagen in {uitvoer}.")


if __name__ == "__main__":
    main()
