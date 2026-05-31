# Hackintosh — HP 245 G8 (Ryzen 3 5300U / Lucienne) + NootedRed

> **Objetivo actual**: Conseguir que arranque el instalador de macOS Ventura/Sonoma con aceleración gráfica usando NootedRed en este portátil específico.

## Hardware

| Componente     | Detalle                                      |
|----------------|----------------------------------------------|
| Modelo         | HP 245 G8 Notebook PC                        |
| CPU            | AMD Ryzen 3 5300U (4C/8T, Zen 2, Lucienne)   |
| iGPU           | AMD Lucienne [1002:164c] (Vega 6)            |
| RAM            | 14 GB DDR4                                   |
| Almacenamiento | Kingston NV3 NVMe (DRAM-less)                |
| WiFi           | Realtek RTL8822CE (sin soporte nativo)       |
| Audio          | Realtek ALC236                               |
| BIOS           | F.30 (AMI)                                   |
| Pantalla       | eDP 1366x768 (interno)                       |

**Notas importantes de hardware**:
- WiFi no funciona en macOS → usar dongle USB-Ethernet (RTL8153 recomendado).
- VRAM subida a **2 GB** en BIOS (crítico para NootedRed).
- No tiene Above 4G Decoding fácil → usamos `npci=0x3000`.

## Estado actual (después de limpieza + mejoras)

- Repositorio limpio y sincronizado con GitHub.
- Generador (`05_generate_config.py`) actualizado con **toggles fáciles** para pruebas:
  - `USE_NRED_DP_DELAY`
  - `USE_MINIMAL_ACPI_FOR_FB_TEST`
- Script de sincronización mejorado (muestra el perfil actual al sincronizar).
- Historial completo de bisección en `macos/docs/DIAGNOSTICO.md`.

## Uso rápido (generar + sincronizar)

```bash
cd macos

# 1. Edita los toggles según el test que quieras hacer
#    (ver sección "Tests recomendados" más abajo)
nano scripts/05_generate_config.py

# 2. Regenera el config.plist
python3 scripts/05_generate_config.py

# 3. Valida
./tools/ocvalidate ./EFI/OC/config.plist

# 4. Sincroniza al USB (USB debe estar montado)
./scripts/06_sync_usb_efi.sh

# O con variables:
USB_LABEL=MACOS MOUNT_POINT=/run/media/$USER/MACOS ./scripts/06_sync_usb_efi.sh
```

**Importante**: Siempre usa un puerto **USB 2.0 (negro)** para el pendrive del instalador durante las pruebas.

## Tests recomendados (orden sugerido)

### Tests ya implementados (toggles en el generador)

| # | Test | Cómo activarlo | Qué esperamos ver |
|---|------|----------------|-------------------|
| 1 | **Con -NRedDPDelay + HDMI externo** | `USE_NRED_DP_DELAY = True` (default) | Arranca en monitor externo aunque el interno quede negro |
| 2 | **ACPI Minimal (estilo Otus)** | `USE_MINIMAL_ACPI_FOR_FB_TEST = True` | Menos errores AE_ALREADY_EXISTS en verbose. ¿Pasa más lejos el framebuffer? |

### Otros tests pendientes (después de los anteriores)

Después de probar 1 y 2, debemos hacer:

1. **Sin NootedRed** (`-radvesa` o deshabilitar el kext) → ¿llega al instalador en VESA?
2. **Sonoma en vez de Ventura** (cambiar recovery).
3. **SMBIOS alternativo** (MacBookPro16,2 vs iMac20,1).
4. **ACPI aún más minimal** (solo los 6-7 SSDTs más básicos del Otus + los críticos de tu DSDT).
5. **NootedRed nightly / versión más nueva** (si 0.8.10 sigue fallando).
6. **DeviceProperties mínimas para iGPU** (aunque las guías recomienden vacío).
7. **Probar en puerto USB 3.0 vs 2.0** (para descartar problemas de enumeración).
8. **Instalación completa + post-instalación** (una vez que pase el instalador).

## Estructura del proyecto

```
hp-245-g8-jemg/
├── README.md                     ← Este archivo
├── macos/
│   ├── EFI/OC/                   ← EFI actual (generada)
│   ├── scripts/
│   │   ├── 05_generate_config.py ← Generador principal (con toggles)
│   │   └── 06_sync_usb_efi.sh    ← Sincronización a USB
│   ├── docs/
│   │   └── DIAGNOSTICO.md        ← Bitácora completa de bisección
│   └── docs/otus9051-hp15s/      ← Referencia que SÍ arranca (mismo CPU)
└── .claude/                      ← Customizaciones de Ruflo / Claude Code
```

## Enlaces útiles indexados

- [Dortania AMD Zen Guide](https://dortania.github.io/OpenCore-Install-Guide/AMD/zen.html)
- [ChefKiss NootedRed](https://github.com/ChefKissInc/NootedRed)
- [ChefKiss Hackintosh Guide](https://chefkiss.dev/guides/hackintosh/)

## Notas finales

- Este repo está optimizado para **bisección rápida** del problema de framebuffer con NootedRed en este hardware específico.
- No intentes instalar todavía. El objetivo actual es **pasar el instalador** (aunque sea en HDMI externo).
- Una vez que funcione el instalador, el siguiente paso será USB mapping real + audio + trackpad.

---

## Sync Script (06_sync_usb_efi.sh)

El script de sincronización ha sido mejorado significativamente:

- Prefiere montar sin sudo usando `udisksctl` cuando es posible.
- Ejecuta `rsync` sin sudo cuando el punto de montaje es escribible por el usuario.
- Por defecto hace **sync completo** (incluye todos los recursos, audios incluidos). Esto es más seguro porque OpenCore podría notar archivos faltantes aunque `AudioSupport=false`.
- Para sync rápido durante muchas iteraciones de prueba:

  ```bash
  SYNC_FAST=1 ./scripts/06_sync_usb_efi.sh
  ```

  Esto excluye `OC/Resources/Audio/` (los ~360 archivos .mp3 del tema gráfico).

El script también muestra el perfil actual del generador al terminar (si tienes `-NRedDPDelay` y si estás en modo ACPI minimal).

## Estado actual de pruebas (2026)

- **Sin acceso a HDMI externo por el momento**. El test principal que recomendaba monitor externo queda bloqueado temporalmente.
- Se está trabajando con la pantalla interna + flags de NootedRed.
- El sync script ahora incluye los archivos de audio por defecto (por seguridad).

## Flujo de trabajo recomendado

```bash
# 1. Editar toggles en el generador
nano scripts/05_generate_config.py

# 2. Regenerar + validar
python3 scripts/05_generate_config.py
./tools/ocvalidate ./EFI/OC/config.plist

# 3. Sincronizar (completo por defecto)
./scripts/06_sync_usb_efi.sh

# O versión rápida (sin audios)
SYNC_FAST=1 ./scripts/06_sync_usb_efi.sh
```

## Notas finales

- Este repo está optimizado para **bisección rápida** del problema de framebuffer con NootedRed.
- No intentes instalar todavía. El objetivo actual es **pasar el instalador**.
- Una vez que funcione el instalador, el siguiente paso será USB mapping real + audio + trackpad.

**Última actualización**: Sync script actualizado para incluir audios por defecto (SYNC_FAST para velocidad). Documentación completa de workflow actual.

---

¿Quieres que prepare el próximo paso de pruebas (por ejemplo, estrategia sin HDMI + flags de NootedRed)? Dime cómo seguimos.
