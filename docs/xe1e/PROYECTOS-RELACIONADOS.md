# Proyectos alrededor del TEF668x: qué tomar para un proyecto propio

Revisión del 2026-10-16 para XE1E. Se buscaron los desarrollos más activos alrededor del
sintonizador **NXP TEF668x** (TEF6686/6687/6688/6689) y se revisó su **código**, no sólo sus
README, con la meta de un firmware propio para el **Deepelec DP-666** que no se limite a FM:
también **onda corta (HF), media (MW) y larga (LW)**.

Marcas: **[verificado]** = revisado en código, binario o documento; **[sin verificar]** =
inferencia o dicho por terceros sin confirmar.

## Índice

1. [Resumen y recomendación](#1-resumen-y-recomendación)
2. [Lo que dice el chip: límites que mandan sobre todo](#2-lo-que-dice-el-chip-límites-que-mandan-sobre-todo)
3. [Firmware base y alternativas completas](#3-firmware-base-y-alternativas-completas)
4. [Forks de PE5PVB con cambios propios](#4-forks-de-pe5pvb-con-cambios-propios)
5. [Firmwares de fabricantes (Megatron y otros)](#5-firmwares-de-fabricantes-megatron-y-otros)
6. [Espectro, barrido y monitoreo](#6-espectro-barrido-y-monitoreo)
7. [Bibliotecas y hardware de referencia](#7-bibliotecas-y-hardware-de-referencia)
8. [Ideas a tomar, ordenadas por banda](#8-ideas-a-tomar-ordenadas-por-banda)
9. [Licencias: qué se puede copiar y qué sólo inspirar](#9-licencias-qué-se-puede-copiar-y-qué-sólo-inspirar)
10. [Propuesta de proyecto propio](#10-propuesta-de-proyecto-propio)
11. [Correcciones al análisis del waterfall](#11-correcciones-al-análisis-del-waterfall)

---

## 1. Resumen y recomendación

- **El hallazgo más importante es `zeevy/tef668x-esp32`**: un firmware **escrito desde cero**
  (octubre de 2026, 86 commits en 12 días, GPLv3) para el **ATS-125**, un radio con hardware casi
  igual al DP-666 (ESP32-WROOM-32U sin PSRAM, ILI9341 320×240, táctil XPT2046, teclado por
  expansor I2C, TEF6686). Tiene la arquitectura que un proyecto propio querría: núcleo en C
  **probado en la PC** (59 suites de pruebas, ≥95 % de cobertura), una tarea del radio en un núcleo
  del ESP32, interfaz con **LVGL**, web con API, OTA, y ya trae **band scope en todas las
  bandas, también en onda corta por banda de metros**. Midió en hardware cuánto hay que esperar
  para leer bien el nivel: **FM 5 ms, AM 40 ms**.
- **PE5PVB** sigue siendo la referencia madura (es el firmware oficial del DP-666), pero es un
  programa monolítico (un `.ino` de ~5800 líneas) difícil de extender a fondo.
- **En AM/HF lo más rico está en el propio chip**, no en los firmwares: hay funciones del TEF
  que nadie usa (high-cut de AM, parámetros extendidos del noise blanker, lectura del AGC,
  medición de offset con 0.1 kHz de resolución, aviso de calidad por GPIO).
- **Megatron** (firmware táctil del DP-666) es el que más funciones de AM/SW agregó (búsqueda por
  rango de SW, escaneo DX en AM, etiquetas propias por frecuencia), pero **sólo es binario**:
  ideas sí, código no.
- **Para espectro y monitoreo**, las mejores ideas vienen del ecosistema de **FM-DX Webserver**
  (barrido diferencial, retención de picos, calibración) y de **autodx** (detección de aperturas
  contra una línea base por canal).

**Recomendación:** un **proyecto propio** (repo nuevo, GPLv3) que parta de la **arquitectura y
el código de `zeevy/tef668x-esp32`**, adaptado al DP-666, y que se diferencie por lo que nadie
ha hecho bien: **AM/HF/MW/LW** (DX de onda media, onda corta por bandas, offset y co-canal,
registros de propagación) y el **waterfall/espectro** con modo de cambios y alertas. El fork de
PE5PVB se queda como referencia y como «firmware de uso diario» mientras tanto. Detalle en la
sección 10.

---

## 2. Lo que dice el chip: límites que mandan sobre todo

Fuente: *User Manual TEF668X /V102 Rev 1.6* (NXP, 2015) **[verificado]**, más mediciones de
otros proyectos.

### Modos de sintonía (`Tune_To`, comando 1)

| Modo | Nombre | Qué hace | FM | AM |
|---|---|---|---|---|
| 1 | Preset | Sintoniza; mute de ~32 ms (FM) / ~60 ms (AM) | Sí | Sí |
| 2 | Search | Igual, pero **se queda en mute** (lo libera el modo 7) | Sí | Sí |
| 3 | AF-Update | Mide otra frecuencia y **regresa** con mute inaudible, ~6 ms | Sí | **No** |
| 4 | Jump | Cambio rápido con mute mínimo | Sí | **No** |
| 5 | Check | Como Jump pero en mute (para verificar PI) | Sí | **No** |
| 7 | End | Libera el mute de Search/Check | Sí | Sí |

**Consecuencia:** en AM (LW/MW/SW) **no hay forma de medir otra frecuencia sin cortar el
audio**. Un monitor de fondo mientras escuchas sólo es posible en FM.

### Tiempo para leer bien el nivel (lo que define la velocidad de un barrido)

| Fuente | FM | AM |
|---|---|---|
| PE5PVB (barrido XDR) | 5 ms | 8 ms |
| zeevy, **medido en el ATS-125** | 5 ms + 4 lecturas | **40 ms + 4 lecturas**: con 5-15 ms la lectura sale 1.6-1.9 dB alta en promedio y 1 de cada 20 se va 6-9 dB |
| oliviercmb, **medido** | modo Search + 4 ms; con 3 ms los picos se ensanchan | sin medir |
| Driver de referencia NXP (`Radio_CheckStation`) | 4 ms, 2 lecturas | 36 ms, 3 lecturas |
| FM-DX-Tuner (Konrad) | espera a que la marca de tiempo del chip diga ≥2 ms | lo mismo (zeevy dice que en AM eso no basta) |

### Lo que el chip puede medir en AM (`Get_Quality`)

- **Nivel** −20…120 dBµV (0.1 dB).
- **Ruido** de alta frecuencia, 0-5000 % respecto a la señal.
- **Co-canal**: bandera 0/1. Detecta un **heterodino subsónico** (otra estación en el mismo canal
  con portadora un poco distinta). Sensibilidad 50-150 %, contador 1-15.
- **Offset** −120…+120 kHz con **resolución de 0.1 kHz**.
- **Modulación** 0-100 % (hasta 200 % en picos).
- **Marca de tiempo** de la medición (0.1-32 ms), para saber cuándo ya es válida.

### Lo que el chip NO hace

- **SSB, BFO, CW, AM síncrono, AM estéreo**: no existen en el TEF668x.
- **Ancho de banda AM**: según el manual NXP, sólo **3, 4, 6 u 8 kHz** (la biblioteca de
  SamuelCicuitStudio documenta 3.0-8.0 continuo; contradice al manual: **probar**).
- **Preamplificador o sintonía de antena** en AM: sólo un **atenuador** de 0 a 36 dB. Por eso en
  SW rinde menos que un Si4735 (conclusión de lalith-ais).
- **HD Radio / DRM**: sólo el TEF6688/6689 saca banda base digital, y necesita decodificador
  externo. El DP-666 trae TEF6686.

### Rangos oficiales vs. usados

NXP especifica LW 144-288, MW 522-1710 y SW 2300-27000 kHz. Los firmwares usan LW hasta 513, MW
hasta 1791 y SW desde 1700: funciona en la práctica, pero fuera de especificación.

---

## 3. Firmware base y alternativas completas

### 3.1 PE5PVB/TEF6686_ESP32 (referencia, firmware oficial del DP-666)

- GPLv3, 365 estrellas, muy activo, autor principal PE5PVB con muchos colaboradores.
- Un `.ino` de ~5800 líneas más `src/` (gui 5800, comms, rds, logbook, touch…). TFT_eSPI.
- El DP-666 es una opción de compilación (`DEEPELEC_DP_66X`).
- **AM ya incluido** [verificado]: LW/MW/SW (y AIR con `HAS_AIR_BAND`), pasos 1/10/100/1000 kHz,
  modo de salto por **bandas de metros** (160 a 11 m) y mostrar la longitud de onda; softmute AM
  (on/off, 25 dB fijo), **noise blanker AM** 50-150 %, **detector co-canal** con sensibilidad y
  contador e indicador «CO», **atenuador** 0-36 dB, **AGC AM** 94-102 dBµV, offset de nivel,
  ancho 3/4/6/8 kHz, indicador de afinación por offset (±0.2 kHz), seek y squelch automático
  por ruido y offset.
- **Le falta** [verificado]: auto-memoria y escáner DX **sólo en FM**; sin nombres propios por
  frecuencia; sin high-cut AM; NB de audio siempre al 100 %; espera fija de 50 ms en el seek AM
  en vez de la marca de tiempo; sin lectura de AGC.
- Observación: PE5PVB **revirtió** en marzo de 2026 varios PR grandes hechos con ayuda de IA
  (accesibilidad de kazek5p). Si algún día se le propone algo, que sea chico y probado.

### 3.2 zeevy/tef668x-esp32 ⭐ (firmware nuevo; candidato a base)

- **GPLv3**, creado el 4-oct-2026, 86 commits, releases v0.1 a v0.4 (15-oct). Un solo autor
  humano (que ya tiene PR aceptados en PE5PVB).
- **Tecnología:** Arduino sobre ESP-IDF con PlatformIO (pioarduino, core 3.3.12), **LVGL 9.5**
  (24 KB de memoria, dibujo en franjas de 10 líneas: funciona sin PSRAM), pantalla a 40 MHz,
  web en Preact + Tailwind empaquetada, binario de ~1.97 MB.
- **Arquitectura** [verificado]: capas `board/`, `drivers/`, `core/`, `ui/`, `net/`; el **núcleo
  es C puro sin hardware**, compilado y probado en la PC (`[env:native]`, Unity), con pruebas que
  reproducen **capturas reales del radio**; tarea del radio en el núcleo 0 (dueña del TEF, RDS cada
  43 ms) y pantalla/entradas/web en el núcleo 1, con colas; I2C con mutex y la **menor
  corriente de manejo en SDA/SCL** para meter menos ruido al sintonizador; todo lo de la placa en
  un header (`board_ats125.h`).
- **Funciones:** LW 144-513, MW 9/10 kHz (región América), **SW 1700-27000 por bandas de
  metros** (160 a 11 m), OIRT y FM por región; AM con anchos 3/4/6/8, **noise blanker
  50-150 %** (RF y audio), high cut y soft mute por nivel, co-canal fijo; **seek AM por ruido y
  offset** con umbrales medidos; squelch Off/Auto/Manual; **AGC de volumen por software**
  (iguala volumen entre estaciones: la dispersión bajó de ~9 dB a 1.6 dB en 10 emisoras);
  **band scope** en todas las bandas (FM ~4 s, MW ~7.5 s, LW ~2 s, 22 m ~3 s), 8 barridos
  guardados con **línea base por mediana, piso de ruido, pico retenido y «subida» sobre la base**,
  cascada en la web, CSV/PNG; **modo DX** (FM: se detiene en estaciones nuevas por PI, registro
  automático, vigilancia de presets en segundo plano); **logbook** 250 entradas, 99 presets con
  CSV; **protocolo XDR** por TCP 7373 o USB (compatible con XDR-GTK y FM-DX Webserver); API
  HTTP, WebSocket a 2 Hz, **OTA con regreso automático** y verificación sha256.
- **Para el DP-666** [sin verificar, a revisar con el diagrama]: coinciden procesador, pantalla,
  táctil, tipo de teclado (el XL9555 del DP-666 es compatible en registros con el PCA9555 del
  ATS-125, dirección 0x20) y sintonizador. Falta: un `board_dp666.h` con los pines (están en el
  diagrama V2.5.4 que ya tenemos), el mapeo de teclas, el sensado del cristal (el DP-666 usa
  12 MHz con divisor de voltaje, igual que el ATS-125) y, sobre todo, **la flash**: el DP-666
  tiene **4 MB** y zeevy está hecho para **8 MB** (dos ranuras OTA de 3 MB). Con 4 MB habría que
  usar una sola ranura o compactar.
- **Debilidades:** 12 días de vida y un solo mantenedor; sólo probado con TEF6686 V102; AM limitado
  a 4 anchos, sin AGC AM ni atenuador en la interfaz; el modo DX es sólo FM; aún no hay espectro en
  vivo en pantalla (sólo en la web).

### 3.3 zeevy/TEF6686_ESP32, rama `dev` (antecedente)

13 commits sobre PE5PVB para el ATS-125: arreglo del selector de banda en la sintonía directa
(PR #958 a PE5PVB, abierto), **volumen con el potenciómetro de squelch**, menú que regresa al
renglón de origen, **batería más estable** (promedio de 8, descarta lecturas del ADC2 cuando el
WiFi interfiere), navegación del menú con el teclado y el **AGC de volumen**. Nada de AM/SW.

### 3.4 kkonradpl/FM-DX-Tuner (autor de XDR-GTK)

- GPLv3+, 75 commits (2023-2026), actividad esporádica. **Sin pantalla**: sintonizador que se
  controla desde la PC con el protocolo XDR.
- Multiplataforma (AVR, **ESP32**, STM32 con **audio por USB**), drivers intercambiables (TEF668x,
  SAF7730, SAF775x), detección automática de la variante del chip.
- **Técnicas a reutilizar:** esperar a la **marca de tiempo de calidad** en vez de un retardo fijo;
  promedios en anillo (nivel 100 ms, CCI y BW 300 ms); **`Set_LevelStep`** para que el nivel no
  salte cuando el AGC cambia de paso (útil para S-meter y barridos); AGC expuesto en 4 pasos;
  detector de interferencia de canal adyacente a partir del ancho de banda automático.
- **AM casi sin tocar:** sólo ajusta el offset de nivel.
- Ojo: lee el cristal con `digitalRead` y no distingue 12 MHz: en el DP-666 habría que fijarlo.

---

## 4. Forks de PE5PVB con cambios propios

De ~40 forks recientes, sólo cuatro tienen commits propios.

| Fork | Qué hace | Veredicto |
|---|---|---|
| **johnnyminer/DP666-Waterfall** | Waterfall para el DP-666: `src/waterfall.cpp` (+402 líneas) | **No compila** (falta una comilla en un `#include`) y **no se puede abrir**: el código que lo arranca quedó en una rama del `if` inalcanzable. Barre la banda completa en modo Jump/Preset sin revisar si la medición es válida (~7 ms/punto, ~2 s por renglón en FM), con paso que se ajusta a 300 columnas (en SW sale de ~85 kHz: inútil), sin span, sin cursor, sin audio, y desplaza la imagen leyendo de la pantalla (`readRect`), lento y dependiente del cableado. Subido por la web de GitHub en 25 minutos; parece no probado en hardware. **Tomar:** la estructura de módulo (`Init/Start/Stop/Loop`), guardar y restaurar el estado, la paleta de 256 colores. **No tomar:** el barrido, el dibujo, ni la integración |
| **MCelliotG** (3.er colaborador de PE5PVB; PR #956 abierto) | Pantalla de entrada de frecuencia con teclado en pantalla y selector de banda, que **acepta el teclado físico del DP-666**; menús de pantalla, entradas y dispositivo; 3 temas; táctil más robusto | El mejor código de referencia para una **pantalla completa que captura perilla, botones, táctil y teclado I2C** y los suelta al salir. Vigilar el PR |
| **josepacelli** (55 commits) | PS/RT/PTY «personalizados» por frecuencia para emisoras brasileñas sin RDS, editor en el radio, CSV por la web, clima de open-meteo en el RT | Errores (fuerza el PTY a «Pop Music», Dynamic PTY siempre encendido). **Tomar sólo la idea** de subir y bajar un CSV por el servidor web del radio |
| **kazek5p-git** | Accesibilidad con tonos y «Voice Lite» (revertido por PE5PVB) | Dato útil: `radio.tone()` genera tonos con el propio TEF (avisos sin hardware extra) |

---

## 5. Firmwares de fabricantes (Megatron y otros)

### 5.1 Megatron (firmware táctil del DP-666, mods 15-17)

- Autor chino que firma «Megatron»; Deepelec aloja los binarios. Base: **PE5PVB v2.00.15**
  (rama vieja, sin lo de v2.11/v2.20). **Sin código fuente publicado** (posible incumplimiento de
  la GPL) [verificado: no se encontró]. Parece tener funciones que se desbloquean con número de
  serie o donativo [sin verificar].
- **Lo que agrega** (manual Mod17 y textos del binario) [verificado]:
  - **AM/SW:** **búsqueda de SW limitada a un rango** configurable; **selección de banda de
    metros**; umbral de offset del auto-search en MW/LW ajustado para aceptar estaciones un poco
    fuera de frecuencia; **escaneo DX también en LW/MW/SW/AIR** (PE5PVB lo hace sólo en FM).
  - **Escaneo a memorias:** parámetros separados FM/AM, **muestreo múltiple en AM** (1-30
    muestras, 10-1000 ms de retención cada una), prioridad **calidad o cantidad**, guardado
    sobrescribir/agregar, por banda o por franja horaria, esquemas guardados, pausar la pantalla
    durante la búsqueda.
  - **Memorias:** 99 canales, ordenar y desfragmentar, quitar duplicados, borrar por banda;
    **nombre propio por frecuencia** con color («My frequency name»); listas de frecuencias.
  - **Pantalla:** modo «**pantalla quieta**» y pausa de refresco para **reducir la interferencia
    de la pantalla en señales débiles** (Deepelec afirma mejor escucha en MW/SW) [sin medir].
  - **Otros:** página de 7 atajos táctiles, teclado en pantalla, acciones de pulsación larga por
    tecla, **plan de recepción programado** (encender y sintonizar a una hora), RTC/NTP, control
    por Bluetooth y por comandos serie, protección por batería baja.
- **Valor:** el mejor catálogo de ideas para AM/SW y escaneo; sólo como inspiración.

### 5.2 Otros

| Proyecto | Qué es | Ideas |
|---|---|---|
| SDRRADIO001/TEF6686_DP666 (SPARKELEC) | Descargas del DP-666: manuales, binarios oficiales y de Megatron | — |
| HamGeek-Portable-TEF6686 | Binarios de PE5PVB sin cambios | — |
| HT5280 (zhihuidelon) | Radio de mesa ESP32-S3 + TEF6686, radio por internet, reproductor, tarjeta de sonido USB; cerrado | **Salida «señal presente»**: un pin que sube cuando el squelch encuentra estación (para disparar una grabadora) |
| qdzqm/TEF6686_ESP32C3 | ESP32-C3 + TEF6686 + ILI9341, sin licencia | Trae el **driver de referencia NXP completo** (~2050 líneas) con high-cut, LevelStep, Get_AGC, Get_Processing_Status, Set_Tune_Options; seek no bloqueante con máquina de estados; guardado rotativo en EEPROM |
| lalith-ais/tef6686-esp32 | Arnés de pruebas ESP-IDF | **Saca el audio demodulado por I2S** del TEF al ESP32 (`Set_Dig_IO`, TEF maestro a 44.1 kHz). Concluye que en SW rinde menos que un Si4735 por el front-end AM sin preamplificador |
| Minhkhoa444/tef6686_sw_receiver | STM32 mínimo | — |

---

## 6. Espectro, barrido y monitoreo

### 6.1 Velocidad de barrido medida

| Proyecto | Modo | Espera/punto | Velocidad |
|---|---|---|---|
| PE5PVB (XDR) | FM Jump, AM Preset | 5 / 8 ms | ~6.2 ms/pt FM, ~9.8 ms/pt AM (estimado por Spectrum Graph) |
| **oliviercmb F8605-CMB** | **Search (mute sostenido)**, filtro 56 kHz, I2C 400 kHz con guarda de 50 µs | 4 ms | **FM completa (206 pt) en ~1.1 s, medido** (contra 2.6 s del original) |
| zeevy | FM Jump, AM Preset | 5 ms ×4 / 40 ms ×4 | FM ~4 s, MW ~7.5 s |
| NcMasters WebDX | Preset, cada punto pedido desde el navegador | 25-80 ms | ~7-10 s en FM |
| amironof autodx | Preset | 100 ms | ~21 s por pasada, una por minuto |

### 6.2 Ideas reutilizables

- **AmateurAudioDude / Spectrum Graph** (plugin de FM-DX Webserver, MIT, muy activo): soporta
  **AM/SW** con bandas predefinidas (LW pasos 1 kHz, MW 3 kHz, bandas de 120 a 11 m en 1-2 kHz,
  todas con BW 3 kHz) y limita HF a 3 MHz por el tiempo; **barrido progresivo** que se dibuja
  mientras avanza; **traza de referencia** guardada por antena para comparar; escala relativa,
  **piso de ruido**, **calibración por segmentos de banda**, corrección del pico que cae entre
  puntos, aviso de barrido viejo.
- **Highpoint2000 / Scanner** (GPL): escaneo **sólo donde hay señal** según el espectro;
  excluir locales fuertes y sus canales vecinos; **barrido diferencial: sólo visita canales cuyo
  nivel cambió más de 3 dB** contra el barrido anterior (detector de cambios de propagación);
  **umbral calibrado con una frecuencia vacía de referencia**; arranque automático cuando la MUF
  indica esporádica E.
- **DX-Alert** (GPL): alertas por correo/Telegram con anti-spam (una por estación cada 30 min).
- **amironof / autodx** (CC0): **la mejor heurística de aperturas**: compara la **mediana de los
  últimos 15 min** contra la **mediana histórica del mismo canal y con el mismo estado de AGC**;
  apertura si el nivel sube >6 dB **y** el ancho de banda automático >20 kHz (el TEF sólo abre el
  filtro cuando la señal está limpia). Al detectarla, escucha RDS ~20 s para identificar.
- **fmatic / SignalScope** (sin licencia, sólo idea): clasificador **QUIET / ACTIVE / BURST** de
  una frecuencia con la derivada y la desviación estándar de las últimas 24 muestras, ataque
  rápido y caída lenta. **Sirve en AM/SW** para ver desvanecimiento (QSB) o la llegada de una
  estación de MW al anochecer.
- **LyonelB / bl-fmo** (sin licencia): monitoreo de una estación con **umbral + retardo antes de
  alertar + alerta de restablecimiento con la duración del corte**, registro cada 60 s. Aplica a
  una estación de referencia de MW o una baliza.
- **NcMasters / WebDX** (MIT): **piso de ruido = percentil 10 + 3 dB**; «seek» saltando de pico en
  pico del espectro sin volver a barrer; sintonizar el pico más fuerte; **apagar el WiFi y
  espaciar las lecturas para meter menos ruido** al sintonizador.
- **RDSExpert** (GPL): registro de bandscans con RDS completo, sólo FM.

---

## 7. Bibliotecas y hardware de referencia

- **SamuelCicuitStudio / NXP-TEF668X-Tuner** (MIT, 0.2.0 del 11-oct-2026): expone **todos los
  comandos del manual** con rangos validados. Útil como **documentación ejecutable** de AM:
  RF AGC 94-102, atenuador 0-36, co-canal (reinicio manual/automático), noise blanker RF
  (sensibilidad y **tiempo de blanqueo 25-250 µs**) y de audio (**400-1200 µs**),
  **softmute por modulación** (comando 41, sólo AM), high-cut, LevelStep, **aviso de calidad por
  GPIO (QSI) con retardo de 1-32 ms**, presets de NXP (AM_DX, AM_ACTIVE_ANTENNA). Ojo: sólo trae
  el parche V102 y documenta un ancho AM continuo que el manual no confirma.
- **FMDX-org / tef668x-headless-usb-tuner** (hardware abierto CERN-OHL-W): sintonizador de PC
  (STM32 + TEF6687 V205, tres antenas, audio por USB). Referencia de cómo lo hacen PE5PVB y
  Konrad; no aporta interfaz ni AM.

---

## 8. Ideas a tomar, ordenadas por banda

### 8.1 Onda media (MW) y larga (LW): DX de onda media

1. **Offset numérico y «ajustar a la portadora»** (idea propia a partir del chip): con 0.1 kHz de
   resolución, mostrar «+0.4 kHz» y detectar **estaciones fuera de rejilla** o de rejilla de
   10 kHz escuchadas en 9 kHz; promediar varias lecturas y exigir poco ruido.
2. **Co-canal visible y registrado**: la bandera «CO» en el log y en el escaneo, botón para
   reiniciar el detector.
3. **Registro de propagación día/noche**: nivel de varias estaciones de referencia cada minuto
   (patrón bl-fmo), con gráfica de 24 h: se ve la entrada de la onda de cielo al atardecer.
4. **Escaneo DX en MW/LW** con muestreo múltiple configurable (Megatron) y criterio de **ruido +
   offset** (PE5PVB/zeevy), registrando nivel, ruido, offset y co-canal.
5. **Waterfall de MW de una hora**: un barrido cada 1-2 minutos (MW ~120 canales × 40 ms ≈ 5 s
   por barrido, sin audio en ese momento) para ver cómo se llena la banda al anochecer.
6. **Indicador de sobrecarga** con `Get_AGC` (sugerir atenuador con antena larga).
7. **High-cut de AM** (el chip lo tiene, nadie lo usa) para quitar el silbido de 9/10 kHz de
   canales vecinos.

### 8.2 Onda corta (HF/SW)

1. **Bandas de metros como unidad**: navegar, barrer y escanear por banda (zeevy y PE5PVB ya lo
   tienen; Megatron agrega búsqueda por rango).
2. **Band scope por banda de metros** (49 m = 61 canales × 40 ms ≈ 2.5 s): mapa de qué está al
   aire ahora, con **retención de picos** y **traza de referencia**.
3. **Mapa de ocupación por hora**: barrer las bandas de metros cada X minutos toda la noche y
   guardar la ocupación (qué se oye a qué hora).
4. **Etiquetas propias por frecuencia** (Megatron) y, mejor, una **lista de horarios** de
   emisoras internacionales (formato tipo EiBi, que es pública) para mostrar «qué debería estar»
   en esa frecuencia y hora.
5. **Noise blanker afinado** con los parámetros extendidos (tiempo de blanqueo) para ruido
   urbano y de la propia pantalla.
6. **Reducir el ruido propio**: pantalla quieta, I2C con poca corriente, WiFi apagado al escuchar
   (Megatron, zeevy, WebDX).

### 8.3 FM

1. **Barrido rápido** con modo Search + 4-5 ms (CMB: FM completa en ~1.1 s).
2. **Modo cambios** contra una línea base por canal y **detector de aperturas** (autodx) con
   alertas por WiFi/Telegram (DX-Alert).
3. **Monitor de fondo con AF-Update** mientras escuchas (sólo FM; probar audibilidad).
4. **Barrido diferencial** para el escáner (Highpoint2000).
5. **Lista de estaciones de México** (en México casi no hay RDS).

### 8.4 Generales

1. **Protocolo XDR** (incluido el barrido `Sa/Sb/Sc/Sw/S`): el radio funciona con XDR-GTK,
   FM-DX Webserver y el plugin Spectrum Graph sin escribir clientes.
2. **API web + página propia** con espectro y cascada grandes (zeevy ya tiene la base).
3. **AGC de volumen por software** (zeevy).
4. **Salida o aviso de «señal presente»** (HT5280) y tonos con `radio.tone()`.
5. **Planes de recepción programados** (Megatron): encender a una hora en una frecuencia y
   registrar.
6. **Audio por I2S al ESP32** (lalith-ais): en el DP-666 el I2S del TEF sólo llega a puntos de
   prueba (TP1-TP4); con una modificación de hardware (cablear a GPIO libres, **por verificar en
   el diagrama**) se podría tener audio digital en el ESP32: vúmetro, grabar a la memoria o
   mandar el audio por WiFi. **Experimental.**

---

## 9. Licencias: qué se puede copiar y qué sólo inspirar

| Licencia | Proyectos | Uso en un proyecto propio GPLv3 |
|---|---|---|
| **GPLv3** | PE5PVB, zeevy, FM-DX-Tuner (GPLv3+), FM-DX Webserver, Scanner, DX-Alert, RDSExpert | Se puede copiar código, conservando avisos y licencia |
| **MIT** | WebDX, Spectrum Graph, biblioteca SamuelCicuitStudio | Se puede copiar código (conservar el aviso MIT) |
| **CC0** | autodx | Libre |
| **GPLv2** | XDR-GTK | Sólo referencia (no mezclar en un GPLv3 sin revisar) |
| **Sin licencia** | oliviercmb CMB, bl-fmo, SignalScope, qdzqm, lalith-ais | **Sólo ideas**, no copiar código |
| **Cerrado** | Megatron, HT5280 | Sólo ideas |

El parche del TEF (`Tuner_Patch_Lithio_*`) es de NXP y lo traen todos; NXP no ha publicado
términos para él.

---

## 10. Propuesta de proyecto propio

### 10.1 Base técnica: tres caminos

| Camino | A favor | En contra |
|---|---|---|
| **A. Seguir sobre el fork de PE5PVB** | Funciona hoy en el DP-666; comunidad grande | Código monolítico; cada cosa nueva es pelearse con un `.ino` de 5800 líneas; difícil probar sin el radio |
| **B. Repo propio a partir de `zeevy/tef668x-esp32`** ⭐ | Arquitectura moderna, núcleo probado en la PC (se puede desarrollar y probar mucho **sin el radio**), LVGL, web, OTA, XDR; hardware casi igual; ya tiene scope en AM/SW | Proyecto de 12 días y un solo autor; flash de 8 MB (el DP-666 tiene 4); hay que portar la placa |
| **C. Desde cero** | Libertad total | Rehacer drivers, RDS, interfaz, web: meses antes de llegar a donde B ya está |

**Recomendación: B.** Un repo propio de XE1E (nombre a elegir), GPLv3, que nazca de
`tef668x-esp32` con su historia y créditos, adaptado al DP-666 y orientado a **HF/MW/LW + espectro
+ registros**. Del código de PE5PVB se toma lo que haga falta (es la misma licencia). Se puede
seguir trayendo mejoras de zeevy mientras convenga, sin depender de él.

### 10.2 Primeros pasos (antes y después de tener el radio)

**Sin el radio (se puede empezar ya):**
1. Confirmar con el diagrama del DP-666 los pines (pantalla, táctil, perilla, botones, teclado
   XL9555, batería, cristal) contra `board_ats125.h`; escribir `board_dp666.h`.
2. Diseñar la tabla de particiones para **4 MB** (una ranura de app de ~2.5 MB + datos, o dos
   ranuras compactas si el binario baja) y compilar el firmware para el DP-666.
3. Empezar los módulos del núcleo que se prueban en la PC: espectro (piso de ruido, picos,
   referencia, diferencia), detector de aperturas, clasificador de actividad, lógica de offset y
   co-canal en AM, registro de propagación.

**Con el radio:**
4. Fase 0 de mediciones (tiempos por punto en FM y AM, audibilidad del AF-Update, efecto en RDS,
   ruido de la pantalla y del WiFi en MW/SW).
5. Primera versión en el DP-666 con lo básico funcionando (bandas, sonido, perilla, teclado).
6. Espectro/waterfall en pantalla, luego las funciones de MW/SW de la sección 8.

### 10.3 Riesgos

- **4 MB de flash**: puede obligar a renunciar a la OTA doble o a fuentes grandes.
- **Pines del DP-666** diferentes del ATS-125 (se resuelve con el diagrama).
- **Ruido**: pantalla, WiFi y bus I2C meten ruido en MW/SW; medirlo y dar opciones para apagarlos.
- **Mantenimiento**: un proyecto propio es trabajo continuo; conviene ir publicando versiones
  probadas.

---

## 11. Correcciones al análisis del waterfall

Respecto a `WATERFALL-ANALISIS.md`:

1. **El monitor de fondo con AF-Update es sólo para FM.** En LW/MW/SW no hay modo que mida otra
   frecuencia y regrese: cualquier barrido de AM corta el audio.
2. **En AM cada punto necesita ~40 ms** (medido por zeevy), no 8 ms: MW completa ≈ 5 s por
   renglón (120 canales), una banda de metros de SW ≈ 2.5 s. Sigue siendo útil para vistas de
   minutos u horas (MW al anochecer, ocupación de SW), no para tiempo real.
3. **FM puede ser más rápida** que lo estimado: con modo Search + 4 ms, ~1.1 s por la banda
   completa (CMB). El modo Search, además, evita los «pops» del Preset.
4. El orden de prioridades por banda queda en la sección 8 de este documento.
