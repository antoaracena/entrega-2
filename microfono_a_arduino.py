"""
Micrófono del computador -> Arduino -> Tira LED
------------------------------------------------
Lee el volumen del micrófono en tiempo real y envía al Arduino
un valor 0-255 por USB. El Arduino enciende más LEDs mientras
más fuerte sea el sonido.

Instalar dependencias (en la terminal de VS Code):
    pip install numpy sounddevice pyserial

Ejecutar:
    python microfono_a_arduino.py

IMPORTANTE: cierra el Monitor Serie del Arduino IDE antes de ejecutar
(si no, el puerto queda ocupado).
"""

import sys
import time
from collections import deque

import numpy as np
import serial
import sounddevice as sd
from serial.tools import list_ports

# ================= AJUSTES =================
PUERTO = None          # None = autodetectar. O ponlo a mano: "COM3" (Windows) / "/dev/cu.usbmodem1101" (Mac)
BAUDIOS = 115200       # Debe coincidir con Serial.begin() del Arduino
SAMPLE_RATE = 44100
BLOQUE = 1024          # muestras por lectura (~23 ms) -> baja latencia

MARGEN_DB = 25         # dB sobre el ruido ambiente para que se encienda el 1er LED.
                       #   ALTO = ignora conversación normal, solo reacciona a gritos.
                       #   Si ni gritando prende, bájalo (ej. 15). Si prende hablando, súbelo (ej. 25).
RANGO_DB = 22          # dB adicionales sobre el margen para llenar los 8 LEDs
                       #   menor = se llena con un grito menos fuerte
VENTANA = 10           # cuadros promediados (~165 ms). Filtra golpes, aplausos y ruidos
                       #   cortos: solo un sonido sostenido (como un grito) sube la tira
SUBIDA = 0.5           # 0-1: qué tan rápido sube (1 = instantáneo)
BAJADA = 0.12          # 0-1: qué tan rápido baja (menor = cae más suave)
FPS = 60               # envíos por segundo al Arduino
# ===========================================

nivel_rms = 0.0


def callback_audio(indata, frames, tiempo, status):
    """Se ejecuta automáticamente cada vez que llega un bloque de audio."""
    global nivel_rms
    nivel_rms = float(np.sqrt(np.mean(indata[:, 0] ** 2)))


def a_db(rms):
    return 20 * np.log10(rms + 1e-10)


def buscar_puerto():
    claves = ("arduino", "usbmodem", "usbserial", "ch340", "ttyacm", "ttyusb", "wchusb")
    puertos = list(list_ports.comports())
    for p in puertos:
        texto = f"{p.device} {p.description} {p.manufacturer}".lower()
        if any(c in texto for c in claves):
            return p.device
    print("No encontré el Arduino automáticamente. Puertos disponibles:")
    for p in puertos:
        print(f"  {p.device}  -  {p.description}")
    print("Pon el correcto en la variable PUERTO al inicio del archivo.")
    sys.exit(1)


def main():
    puerto = PUERTO or buscar_puerto()
    print(f"Conectando a Arduino en {puerto} ...")
    arduino = serial.Serial(puerto, BAUDIOS, timeout=0)
    time.sleep(2)  # el Arduino se reinicia al abrir el puerto

    with sd.InputStream(channels=1, samplerate=SAMPLE_RATE,
                        blocksize=BLOQUE, callback=callback_audio):
        # --- Calibración del ruido ambiente ---
        print("Calibrando ruido ambiente... guarden silencio 2 segundos")
        muestras = []
        t0 = time.time()
        while time.time() - t0 < 2:
            muestras.append(a_db(nivel_rms))
            time.sleep(0.02)
        piso = float(np.median(muestras)) + MARGEN_DB
        print(f"Listo. Ruido ambiente ≈ {piso - MARGEN_DB:.1f} dB. ¡A gritar!\n")

        nivel = 0.0
        historial = deque(maxlen=VENTANA)
        try:
            while True:
                historial.append(a_db(nivel_rms))
                db = float(np.mean(historial))   # promedio: ignora ruidos cortos
                objetivo = np.clip((db - piso) / RANGO_DB, 0.0, 1.0)

                # Suavizado: sube rápido, baja lento (se ve más fluido)
                factor = SUBIDA if objetivo > nivel else BAJADA
                nivel += (objetivo - nivel) * factor

                valor = int(nivel * 255)
                arduino.write(bytes([valor]))

                barra = "█" * int(nivel * 40)
                print(f"\r{db:6.1f} dB |{barra:<40}| {valor:3d}", end="", flush=True)

                time.sleep(1 / FPS)
        except KeyboardInterrupt:
            print("\nCerrando...")
        finally:
            arduino.write(bytes([0]))  # apagar LEDs
            arduino.close()


if __name__ == "__main__":
    main()    
    