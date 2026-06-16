"""Stap 1: vacatures ophalen uit alle ingeschakelde bronnen.

Leest config/sources.json (of het example-bestand als die er niet is),
roept elke ingeschakelde provider aan en schrijft de ruwe vacatures naar
data/jobs_raw.json.

Gebruik:  python src/fetch_jobs.py
"""

import json
import os

from providers import (
    adzuna,
    arbeitnow,
    jobicy,
    jooble,
    manual_links,
    nationale_vacaturebank,
    overheid,
    rss,
)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
DATA_DIR = os.path.join(PROJECT_DIR, "data")

# Koppel de naam uit sources.json aan de provider-module.
PROVIDERS = {
    "nationale_vacaturebank": nationale_vacaturebank,
    "overheid": overheid,
    "adzuna": adzuna,
    "jooble": jooble,
    "jobicy": jobicy,
    "rss": rss,
    "arbeitnow": arbeitnow,
    "manual_links": manual_links,
}


def laad_config(naam):
    """Laad een config-bestand; val terug op het .example-bestand."""
    pad = os.path.join(CONFIG_DIR, naam)
    example = os.path.join(CONFIG_DIR, naam.replace(".json", ".example.json"))
    if not os.path.exists(pad) and os.path.exists(example):
        print(f"[fetch] {naam} niet gevonden, gebruik {os.path.basename(example)}.")
        pad = example
    with open(pad, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    sources = laad_config("sources.json")

    alle_vacatures = []
    for naam, module in PROVIDERS.items():
        bron_config = sources.get(naam, {})
        if not bron_config.get("aan", False):
            print(f"[fetch] Bron '{naam}' staat uit, overslaan.")
            continue
        print(f"[fetch] Ophalen uit '{naam}'...")
        vacatures = module.fetch(bron_config)
        print(f"[fetch] {len(vacatures)} vacatures uit '{naam}'.")
        alle_vacatures.extend(vacatures)

    os.makedirs(DATA_DIR, exist_ok=True)
    uitvoer = os.path.join(DATA_DIR, "jobs_raw.json")
    with open(uitvoer, "w", encoding="utf-8") as f:
        json.dump(alle_vacatures, f, ensure_ascii=False, indent=2)

    print(f"[fetch] Totaal {len(alle_vacatures)} vacatures opgeslagen in {uitvoer}.")


if __name__ == "__main__":
    main()
