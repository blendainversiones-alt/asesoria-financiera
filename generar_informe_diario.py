"""Genera un informe diario de mercados (general, argentino y cripto) en Markdown."""

import sys
from datetime import datetime

import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 10

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

GENERAL_MARKETS = [
    ("S&P 500", "%5EGSPC"),
    ("Nasdaq Composite", "%5EIXIC"),
    ("Dow Jones", "%5EDJI"),
    ("EUR/USD", "EURUSD=X"),
    ("Oro (futuro)", "GC=F"),
    ("Petroleo WTI (futuro)", "CL=F"),
    ("Bono Tesoro EE.UU. 10 anios (rendimiento %)", "%5ETNX"),
]

CRYPTO_MARKETS = [
    ("Bitcoin (BTC)", "BTC-USD"),
    ("Ethereum (ETH)", "ETH-USD"),
    ("BNB", "BNB-USD"),
    ("Solana (SOL)", "SOL-USD"),
    ("XRP", "XRP-USD"),
]

DOLAR_LABELS = {
    "oficial": "Oficial",
    "blue": "Blue",
    "bolsa": "MEP (Bolsa)",
    "contadoconliqui": "CCL",
    "mayorista": "Mayorista",
    "cripto": "Cripto",
    "tarjeta": "Tarjeta",
}


def fetch_yahoo(symbol):
    r = requests.get(YAHOO_URL.format(symbol=symbol), headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    result = r.json()["chart"]["result"]
    if not result:
        raise ValueError("sin datos")
    meta = result[0]["meta"]
    price = meta.get("regularMarketPrice")
    prev = meta.get("previousClose")
    change_pct = None
    if price is not None and prev:
        change_pct = (price - prev) / prev * 100
    return price, prev, change_pct


def render_market_table(rows):
    lines = ["| Activo | Ultimo | Cierre anterior | Variacion |", "|---|---|---|---|"]
    for name, symbol in rows:
        try:
            price, prev, pct = fetch_yahoo(symbol)
            price_s = f"{price:,.2f}" if price is not None else "N/D"
            prev_s = f"{prev:,.2f}" if prev is not None else "N/D"
            pct_s = f"{pct:+.2f}%" if pct is not None else "N/D"
        except Exception as exc:  # fuente externa: puede fallar por red o rate limit
            price_s = prev_s = pct_s = f"error ({exc})"
        lines.append(f"| {name} | {price_s} | {prev_s} | {pct_s} |")
    return "\n".join(lines)


def fetch_dolares():
    r = requests.get("https://dolarapi.com/v1/dolares", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def render_dolar_table():
    lines = ["| Tipo | Compra | Venta |", "|---|---|---|"]
    try:
        data = fetch_dolares()
        for item in data:
            label = DOLAR_LABELS.get(item.get("casa"), item.get("nombre", item.get("casa")))
            compra = item.get("compra")
            venta = item.get("venta")
            compra_s = f"${compra:,.2f}" if compra is not None else "N/D"
            venta_s = f"${venta:,.2f}" if venta is not None else "N/D"
            lines.append(f"| {label} | {compra_s} | {venta_s} |")
    except Exception as exc:
        lines.append(f"| error al obtener cotizaciones ({exc}) | | |")
    return "\n".join(lines)


def fetch_riesgo_pais():
    r = requests.get("https://mercados.ambito.com//riesgopais/variacion", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data.get("ultimo"), data.get("fecha"), data.get("variacion")


def render_riesgo_pais():
    try:
        valor, fecha, variacion = fetch_riesgo_pais()
        return f"**Riesgo pais (EMBI+ Argentina):** {valor} pb (variacion {variacion}, dato al {fecha})"
    except Exception as exc:
        return f"**Riesgo pais:** error al obtener dato ({exc})"


def render_merval():
    try:
        price, prev, pct = fetch_yahoo("%5EMERV")
        price_s = f"{price:,.0f}" if price is not None else "N/D"
        pct_s = f"{pct:+.2f}%" if pct is not None else "N/D"
        return f"**Merval:** {price_s} puntos (variacion {pct_s})"
    except Exception as exc:
        return f"**Merval:** error al obtener dato ({exc})"


def build_report():
    now = datetime.now()
    fecha_larga = now.strftime("%d/%m/%Y")
    hora = now.strftime("%H:%M")

    parts = [
        f"# Informe Diario de Mercados - {fecha_larga}",
        f"_Generado automaticamente a las {hora} (hora Argentina)_",
        "",
        "## Mercados generales",
        render_market_table(GENERAL_MARKETS),
        "",
        "## Mercado argentino",
        "",
        "### Dolar",
        render_dolar_table(),
        "",
        "### Indices y riesgo pais",
        render_merval(),
        "",
        render_riesgo_pais(),
        "",
        "## Criptomonedas",
        render_market_table(CRYPTO_MARKETS),
        "",
        "---",
        "_Fuentes: Yahoo Finance, DolarAPI, Ambito Financiero. Informe generado automaticamente; verificar datos antes de tomar decisiones de inversion._",
    ]
    return "\n".join(parts)


def main():
    report = build_report()
    filename = f"Informe_Mercados_{datetime.now().strftime('%Y-%m-%d')}.md"
    from pathlib import Path

    out_path = Path(__file__).parent / filename
    out_path.write_text(report, encoding="utf-8")
    print(f"Informe generado: {out_path}")


if __name__ == "__main__":
    sys.exit(main() or 0)
