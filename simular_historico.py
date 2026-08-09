"""Genera y commitea (con fechas retroactivas) informes de prueba para los ultimos N dias.

Usa datos historicos REALES de Yahoo Finance para mercados generales y cripto.
La seccion Argentina (dolar/Merval/riesgo pais) no tiene API historica gratuita
disponible, asi que se marca explicitamente como dato de referencia actual, no historico.
"""

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import requests

from generar_informe_diario import (
    CRYPTO_MARKETS,
    GENERAL_MARKETS,
    HEADERS,
    TIMEOUT,
    render_dolar_table,
    render_merval,
    render_riesgo_pais,
)

DAYS_BACK = 5
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def fetch_history(symbol, range_="10d"):
    r = requests.get(
        CHART_URL.format(symbol=symbol),
        headers=HEADERS,
        params={"range": range_, "interval": "1d"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    result = r.json()["chart"]["result"]
    if not result:
        raise ValueError("sin datos")
    res = result[0]
    timestamps = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    by_date = {}
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        day = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        by_date[day] = close
    return by_date


def render_market_table_historical(rows, all_history, day_str, prev_day_str):
    lines = ["| Activo | Cierre | Cierre anterior | Variacion |", "|---|---|---|---|"]
    for name, symbol in rows:
        hist = all_history.get(symbol, {})
        price = hist.get(day_str)
        prev = hist.get(prev_day_str)
        if price is not None and prev:
            pct = (price - prev) / prev * 100
            price_s, prev_s, pct_s = f"{price:,.2f}", f"{prev:,.2f}", f"{pct:+.2f}%"
        elif price is not None:
            price_s, prev_s, pct_s = f"{price:,.2f}", "N/D", "N/D"
        else:
            price_s = prev_s = pct_s = "N/D (sin dato para esta fecha)"
        lines.append(f"| {name} | {price_s} | {prev_s} | {pct_s} |")
    return "\n".join(lines)


def build_historical_report(day, all_history, dolar_snapshot, merval_snapshot, riesgo_snapshot):
    day_str = day.strftime("%Y-%m-%d")
    prev_day_str = (day - timedelta(days=1)).strftime("%Y-%m-%d")
    fecha_larga = day.strftime("%d/%m/%Y")

    parts = [
        "# Blenda Inversiones",
        "_Estas a un click de tu independencia financiera_",
        "",
        f"## Informe Diario de Mercados - {fecha_larga}",
        "_[SIMULACION] Informe de prueba generado retroactivamente para validar el flujo automatico._",
        "",
        "## Mercados generales",
        "_Datos historicos reales (Yahoo Finance)._",
        "",
        render_market_table_historical(GENERAL_MARKETS, all_history, day_str, prev_day_str),
        "",
        "## Mercado argentino",
        "_[SIMULACION] Estas fuentes no ofrecen API historica gratuita: se muestra el valor de referencia "
        "actual, no el dato real del dia indicado._",
        "",
        "### Dolar",
        dolar_snapshot,
        "",
        "### Indices y riesgo pais",
        merval_snapshot,
        "",
        riesgo_snapshot,
        "",
        "## Criptomonedas",
        "_Datos historicos reales (Yahoo Finance)._",
        "",
        render_market_table_historical(CRYPTO_MARKETS, all_history, day_str, prev_day_str),
        "",
        "---",
        "_Fuentes: Yahoo Finance (historico real), DolarAPI y Ambito Financiero (valor actual, sin backfill "
        "historico). Informe de simulacion; no usar para decisiones de inversion._",
        "",
        "_Blenda Inversiones - blendainversiones.com_",
    ]
    return "\n".join(parts)


def main():
    repo_dir = Path(__file__).parent
    all_symbols = [s for _, s in GENERAL_MARKETS] + [s for _, s in CRYPTO_MARKETS]
    print("Descargando historico real de Yahoo Finance...")
    all_history = {sym: fetch_history(sym) for sym in all_symbols}

    print("Tomando snapshot actual de fuentes argentinas (sin historico disponible)...")
    dolar_snapshot = render_dolar_table()
    merval_snapshot = render_merval()
    riesgo_snapshot = render_riesgo_pais()

    today = datetime.now()
    for i in range(DAYS_BACK, 0, -1):
        day = today - timedelta(days=i)
        report = build_historical_report(day, all_history, dolar_snapshot, merval_snapshot, riesgo_snapshot)
        filename = f"Informe_Mercados_{day.strftime('%Y-%m-%d')}.md"
        out_path = repo_dir / filename
        out_path.write_text(report, encoding="utf-8")

        commit_dt = day.replace(hour=18, minute=0, second=0, microsecond=0)
        env = os.environ.copy()
        env["GIT_AUTHOR_DATE"] = commit_dt.strftime("%Y-%m-%dT%H:%M:%S")
        env["GIT_COMMITTER_DATE"] = commit_dt.strftime("%Y-%m-%dT%H:%M:%S")
        subprocess.run(["git", "add", filename], cwd=repo_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"[Simulacion] Informe diario {day.strftime('%Y-%m-%d')}"],
            cwd=repo_dir,
            check=True,
            env=env,
        )
        print(f"Generado y commiteado: {filename} (fecha commit: {commit_dt})")

    print("Listo. Revisa 'git log' y luego hace 'git push' para subir la simulacion.")


if __name__ == "__main__":
    main()
