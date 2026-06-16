# GitHub + Pages + dagelijkse run — stappenplan

Dit project is klaar om te publiceren. De stappen hieronder voer je één keer uit
in je **eigen terminal** (en deels op github.com). Ik kan dit niet voor je doen:
een repo aanmaken, pushen en Pages aanzetten vereisen toegang tot jouw
GitHub-account.

## 0. Eenmalig opruimen

Tijdens het bouwen is er een onvolledige `.git`-map achtergebleven die ik vanuit
de sandbox niet kon verwijderen. Ruim die eerst op zodat je schoon begint:

```bash
cd ~/Claude/Projects/"Vacature Radar"
rm -rf .git
```

## 1. Lokale git-repo maken

```bash
git init
git add -A
git commit -m "Vacature Radar versie 1"
```

Controleer dat je geen persoonlijke bestanden meecommit (die staan in
`.gitignore`): er mag GEEN `config/profile.json`, `config/sources.json` of
`data/manual_links.json` in de commit zitten. `git status` moet schoon zijn.

## 2. Repo op GitHub aanmaken en pushen

**Optie A — met de GitHub CLI (`gh`):**

```bash
gh repo create vacature-radar --public --source=. --remote=origin --push
```

**Optie B — via de website:**

1. Maak op github.com een nieuwe **lege** repo `vacature-radar` (zonder README).
2. Koppel en push:

```bash
git branch -M main
git remote add origin https://github.com/<jouw-gebruikersnaam>/vacature-radar.git
git push -u origin main
```

## 3. GitHub Pages aanzetten

1. Ga in de repo naar **Settings → Pages**.
2. Zet **Source** op **GitHub Actions**.

De workflow `.github/workflows/daily.yml` bouwt en publiceert de site al.

## 4. De dagelijkse run

- De workflow draait **elke dag om 06:00 UTC** (≈ 07:00/08:00 NL-tijd).
- Je kunt hem ook handmatig starten: **Actions → "Dagelijkse vacatures" → Run workflow**.
- Na de eerste run staat de site op:
  `https://<jouw-gebruikersnaam>.github.io/vacature-radar/`

Deze link deel je met Kevin.

## 5. (Optioneel) Echte bronnen aanzetten via Secrets

De site werkt meteen met Jobicy (gratis, geen sleutel) en de mock-bron. Voor de
fase-2 bronnen voeg je sleutels toe via **Settings → Secrets and variables →
Actions → New repository secret**:

| Secret-naam      | Voor bron            | Waar te halen                        |
| ---------------- | -------------------- | ------------------------------------ |
| `ADZUNA_APP_ID`  | Adzuna NL            | https://developer.adzuna.com/ (gratis) |
| `ADZUNA_APP_KEY` | Adzuna NL            | idem                                 |
| `JOOBLE_API_KEY` | Jooble               | Jooble Help Center → REST API        |
| `CSO_API_KEY`    | Overheid (CSO)       | account bij Carrière Sites Overheid  |

Zet daarna de betreffende bron in `config/sources.json` op `"aan": true`.
(De workflow leest deze secrets al; zonder secrets worden die bronnen netjes
overgeslagen.)

## Belangrijk

- Sleutels staan **nooit** in de code — alleen als GitHub Secrets.
- De CI gebruikt automatisch de `.example`-configbestanden, dus de site bouwt
  ook zonder dat je je persoonlijke `config/*.json` meepusht.
