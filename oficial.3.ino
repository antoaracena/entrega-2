#include <Adafruit_NeoPixel.h>

#define PIN_DATOS   6
#define NUM_LEDS    6
#define BRILLO      80

Adafruit_NeoPixel tira(NUM_LEDS, PIN_DATOS, NEO_GRB + NEO_KHZ800);

uint8_t nivel = 0;
unsigned long tUltimoDato = 0;

// Amarillo (primer LED) -> rojo (ultimo LED)
uint32_t colorPara(int i) {
  float t = (float)i / (NUM_LEDS - 1);
  uint8_t g = (uint8_t)(255 * (1.0 - t));
  return tira.Color(255, g, 0);
}

void setup() {
  Serial.begin(115200);
  tira.begin();
  tira.setBrightness(BRILLO);
  tira.clear();
  tira.show();
}

void loop() {
  while (Serial.available() > 0) {
    nivel = Serial.read();
    tUltimoDato = millis();
  }
  if (millis() - tUltimoDato > 1000) nivel = 0;

  int encendidos = map(nivel, 0, 255, 0, NUM_LEDS);

  for (int i = 0; i < NUM_LEDS; i++) {
    if (i < encendidos) tira.setPixelColor(i, colorPara(i));
    else                tira.setPixelColor(i, 0);
  }
  tira.show();
  delay(10);
}