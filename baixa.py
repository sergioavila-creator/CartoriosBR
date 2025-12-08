#!/usr/bin/env python3
# baixador_v3_com_log.py — versão discreta (não exibe erros no console)

import os
import re
import time
import requests
from urllib.parse import urljoin, urlparse
from datetime import date

BASE_PAGE = "https://www.tjrj.jus.br/transparencia/relatorio-de-receita-cartoraria-extrajudicial"
ROOT = "https://www.tjrj.jus.br"

PDF_SUBSTR = "documents/d/guest/receita"
OUTDIR = "pdfs"

LOGFILE = "log_baixador.log"

RETRIES = 3
TIMEOUT_CONNECT = 20
TIMEOUT_READ = 120
MIN_PDF_BYTES = 1500

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12
}

def log_error(msg: str):
    """Registra erro silenciosamente no log."""
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def safe_get(url):
    """Baixa HTML sem exibir erros no console."""
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log_error(f"[ERRO HTML] {url} — {e}")
        return ""

def extract_pdf_links(html, base=ROOT):
    if not html:
        return []

    found = []
    seen = set()

    regex = re.compile(r'href\s*=\s*(["\']?)(?P<u>[^"\' >]+)', re.I)

    for m in regex.finditer(html):
        raw = m.group("u")

        if PDF_SUBSTR not in raw.lower():
            continue

        if raw.startswith("//"):
            url = "https:" + raw
        elif raw.startswith("/"):
            url = urljoin(base, raw)
        else:
            url = raw

        p = urlparse(url)
        clean = p.scheme + "://" + p.netloc + p.path
        if p.query:
            clean += "?" + p.query

        if clean not in seen:
            seen.add(clean)
            found.append(clean)

    return found

def extrair_mes_ano(url):
    nome = os.path.basename(url).lower()

    mes = None
    for nome_mes, numero in MESES.items():
        if nome_mes in nome:
            mes = numero
            break

    ano_m = re.search(r"20\d{2}", nome)
    ano = int(ano_m.group()) if ano_m else None

    return (mes, ano) if mes and ano else (None, None)

def download_stream(url, dest):
    """Download robusto com retries — erros só no log."""
    for attempt in range(1, RETRIES + 1):
        try:
            with requests.Session() as s:
                r = s.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    stream=True,
                    timeout=(TIMEOUT_CONNECT, TIMEOUT_READ)
                )
                r.raise_for_status()

                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            if os.path.getsize(dest) < MIN_PDF_BYTES:
                raise Exception("Arquivo muito pequeno")

            with open(dest, "rb") as f:
                if b"%PDF" not in f.read(10):
                    raise Exception("Assinatura PDF inválida")

            print(f"[OK] {os.path.basename(dest)}")
            return True

        except Exception as e:
            log_error(f"[DOWNLOAD ERRO {attempt}/{RETRIES}] {url} — {e}")
            time.sleep(1 + attempt * 2)

    log_error(f"[FALHA] {url}")
    return False

def main():
    print("=== BAIXADOR v3 (com LOG) ===")

    os.makedirs(OUTDIR, exist_ok=True)

    print("Carregando principal...")
    html_main = safe_get(BASE_PAGE)
    links_main = extract_pdf_links(html_main)
    print(f"→ {len(links_main)} links")

    ano_ant = date.today().year - 1

    print(f"Carregando {ano_ant}...")
    html_prev = safe_get(f"{BASE_PAGE}/{ano_ant}")
    links_prev = extract_pdf_links(html_prev)
    print(f"→ {len(links_prev)} links")

    combined = list(dict.fromkeys(links_main + links_prev))

    print(f"Total bruto: {len(combined)}")

    def key(u):
        mes, ano = extrair_mes_ano(u)
        return ano * 100 + mes if mes and ano else 0

    combined.sort(key=key, reverse=True)

    print("\nBaixando 12 arquivos...\n")
    baixados = 0

    for url in combined:
        if baixados >= 12:
            break

        mes, ano = extrair_mes_ano(url)

        if mes and ano:
            nome = f"{ano} {mes:02d}.pdf"
        else:
            nome = f"arquivo_{baixados+1:02d}.pdf"

        dest = os.path.join(OUTDIR, nome)

        if download_stream(url, dest):
            baixados += 1

    print(f"\nConcluído: {baixados}/12 baixados")
    print(f"Logs registrados em: {LOGFILE}")

if __name__ == "__main__":
    main()
