"""Optionele JS-rendering met Playwright.

Sommige bronnen renderen hun vacaturedetailpagina volledig met JavaScript
(bijv. Nationale Vacaturebank): de statische HTML is een lege app-shell zonder
JSON-LD. Met een headless browser laden we de pagina alsnog en lezen we de
JobPosting-data uit de gerenderde HTML.

Bewust optioneel en defensief:
- Valt netjes terug als Playwright/Chromium niet geïnstalleerd is (geen crash,
  alleen geen verrijking).
- Cachet de gerenderde HTML naast de gewone scrape-cache.
- Houdt dezelfde interface als PoliteSession (`.get(url)` + `.bron`), zodat
  `_polite.verrijk_met_detailpagina` er direct mee werkt.

Inschakelen per bron met "render_js": true in config/sources.json. Knoppen:
  "render_timeout_ms" (standaard 30000), "render_wait" (standaard "networkidle").
"""

import time

from . import _polite


class BrowserRenderer:
    """Headless-browser renderer met cache, delay en nette fallback."""

    # Realistische desktop-UA i.p.v. de default 'HeadlessChrome' (die sites als
    # Indeed blokkeren).
    STANDAARD_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36")

    def __init__(self, bron, config):
        self.bron = bron
        self.delay = max(0, float(config.get("delay_seconds", 0)))
        self.timeout = int(config.get("render_timeout_ms", 30000))
        self.wait = config.get("render_wait", "networkidle")
        self.user_agent = config.get("user_agent") or self.STANDAARD_UA
        self.locale = config.get("render_locale", "nl-NL")
        self._pw = None
        self._browser = None
        self._page = None
        self._beschikbaar = None  # None = nog niet geprobeerd
        self._laatste_request = 0.0

    def _start(self):
        if self._beschikbaar is not None:
            return self._beschikbaar
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print(f"[{self.bron}] Playwright niet geïnstalleerd; JS-verrijking overgeslagen.")
            self._beschikbaar = False
            return False
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                args=["--disable-blink-features=AutomationControlled"]
            )
            self._page = self._browser.new_page(
                user_agent=self.user_agent,
                locale=self.locale,
                viewport={"width": 1280, "height": 900},
            )
            self._beschikbaar = True
        except Exception as fout:  # noqa: BLE001
            print(f"[{self.bron}] Browser starten mislukt ({fout}); JS-verrijking overgeslagen.")
            self._beschikbaar = False
        return self._beschikbaar

    def get(self, url):
        """Render een pagina (of lees uit cache). Geeft HTML of None."""
        cache_pad = _polite._cache_pad(self.bron, url) + ".rendered"
        gecachet = _polite._lees_cache(cache_pad)
        if gecachet is not None:
            return gecachet

        if not self._start():
            return None

        wacht = self.delay - (time.time() - self._laatste_request)
        if wacht > 0:
            time.sleep(wacht)
        try:
            self._page.goto(url, wait_until=self.wait, timeout=self.timeout)
            html = self._page.content()
        except Exception as fout:  # noqa: BLE001
            print(f"[{self.bron}] Render mislukt voor {url}: {fout}.")
            return None
        finally:
            self._laatste_request = time.time()

        _polite._schrijf_cache(cache_pad, html)
        return html

    def close(self):
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:  # noqa: BLE001
            pass
