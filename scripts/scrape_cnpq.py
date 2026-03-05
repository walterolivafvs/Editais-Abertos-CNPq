#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Scraper opcional (local) para gerar data.json a partir do gov.br (CNPq).

Uso:
  python3 scripts/scrape_cnpq.py

Observação:
- O painel (GitHub Pages) NÃO depende deste script.
- Você pode continuar atualizando o data.json manualmente.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_LIST_URL = "https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao"
OUT_JSON = "data.json"
SEED_FILE = "seed_url.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/123.0 Safari/537.36"
}

DATE_RANGE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})", re.I)

def ddmmyyyy_to_iso(s: str) -> str:
    try:
        return datetime.strptime(s, "%d/%m/%Y").date().isoformat()
    except Exception:
        return ""

def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def extract_list_items(html: str):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for h2 in soup.find_all("h2"):
        a = h2.find("a", href=True)
        if not a:
            continue
        href = a["href"].strip()
        # aceitar links relativos do gov.br
        full = urljoin(BASE_LIST_URL, href)
        title = " ".join(a.get_text(" ", strip=True).split())
        if not title:
            continue
        items.append({"title": title, "url": full})
    # fallback: seed manual
    if not items:
        seed_path = Path(__file__).resolve().parent / SEED_FILE
        if seed_path.exists():
            seed = json.loads(seed_path.read_text(encoding="utf-8"))
            for it in seed.get("items", []):
                if it.get("title") and it.get("url"):
                    items.append({"title": it["title"], "url": it["url"]})
    return items

def extract_deadline_from_detail(detail_html: str) -> str:
    # procura padrão "Inscrições: ... dd/mm/yyyy a dd/mm/yyyy"
    txt = BeautifulSoup(detail_html, "html.parser").get_text("\n", strip=True)
    m = DATE_RANGE_RE.search(txt)
    if not m:
        return ""
    return ddmmyyyy_to_iso(m.group(2))

def main():
    list_html = fetch(BASE_LIST_URL)
    base_items = extract_list_items(list_html)

    enriched = []
    for it in base_items:
        deadline = ""
        try:
            detail_html = fetch(it["url"])
            deadline = extract_deadline_from_detail(detail_html)
        except Exception:
            deadline = ""

        enriched.append({
            "title": it["title"],
            "url": it["url"],
            "area": "Geral",
            "type": "Chamada",
            "date": deadline
        })

    out = {
        "source": {"name": "CNPq — Chamadas Abertas para Submissão", "url": BASE_LIST_URL},
        "updated_at": datetime.now().date().isoformat(),
        "items": enriched
    }

    out_path = Path(__file__).resolve().parents[1] / OUT_JSON
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {out_path} ({len(enriched)} itens)")

if __name__ == "__main__":
    main()
