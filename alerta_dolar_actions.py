"""
Bot de alerta de precio del dólar (USD/CLP) vía Telegram — versión para
GitHub Actions.

Diferencias respecto a la versión de "loop infinito" (alerta_dolar.py):
- Corre UNA sola vez y termina (GitHub Actions lo vuelve a ejecutar cada
  N minutos según el cron del workflow, no hay que dejarlo corriendo).
- TOKEN y CHAT_ID se leen desde variables de entorno (los "secrets" de
  GitHub), nunca quedan escritos en este archivo.
- El estado ("ya avisado" / "no avisado") se guarda en un archivo de texto
  (estado.txt) para no repetir la alerta cada 5 minutos mientras el precio
  siga bajo el umbral. El workflow se encarga de subir ese archivo de
  vuelta al repositorio después de cada ejecución.
"""

import os
import requests

UMBRAL = 2000  # CLP por USD
ESTADO_ARCHIVO = "estado.txt"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/CLP=X"


def obtener_precio_dolar():
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(YAHOO_URL, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return round(data["chart"]["result"][0]["meta"]["regularMarketPrice"], 2)


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje}, timeout=10)
    if resp.status_code != 200:
        print(f"[ERROR] No se pudo enviar el mensaje a Telegram: {resp.text}")
    else:
        print("[OK] Alerta enviada a Telegram.")


def leer_estado():
    if not os.path.exists(ESTADO_ARCHIVO):
        return "no_avisado"
    with open(ESTADO_ARCHIVO, "r") as f:
        return f.read().strip()


def guardar_estado(estado):
    with open(ESTADO_ARCHIVO, "w") as f:
        f.write(estado)


def main():
    if not TOKEN or not CHAT_ID:
        raise SystemExit(
            "Faltan las variables de entorno TELEGRAM_TOKEN o TELEGRAM_CHAT_ID. "
            "Revisa que los secrets estén bien configurados en GitHub."
        )

    precio = obtener_precio_dolar()
    estado_anterior = leer_estado()
    print(f"Precio actual: ${precio} CLP | Estado anterior: {estado_anterior}")

    if precio < UMBRAL and estado_anterior == "no_avisado":
        mensaje = (
            f"🔔 ¡El dólar bajó de ${UMBRAL}!\n"
            f"Precio actual: ${precio} CLP"
        )
        enviar_telegram(mensaje)
        guardar_estado("avisado")

    elif precio >= UMBRAL and estado_anterior == "avisado":
        guardar_estado("no_avisado")
        print("El precio volvió a subir del umbral. Alerta rearmada.")

    else:
        # Sin cambio de estado, no se hace nada.
        guardar_estado(estado_anterior)


if __name__ == "__main__":
    main()
