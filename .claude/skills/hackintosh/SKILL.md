---
name: "Hackintosh HP 245 G8 — Ryzen 5300U + NootedRed"
description: "Especialista en EFI OpenCore para HP 245 G8 (Ryzen 3 5300U, Lucienne, Vega 6). Úsame para diagnosticar boots, editar el generador, arreglar kexts/SSDTs, sincronizar al USB, o investigar problemas de input/framebuffer. Fuente de verdad: macos/scripts/05_generate_config.py."
---

# Hackintosh HP 245 G8 — Ryzen 3 5300U + NootedRed

## Hardware verificado

| Componente | Detalle |
|---|---|
| CPU | AMD Ryzen 3 5300U (4C/8T, Zen 2, Lucienne) |
| iGPU | AMD Vega 6 `1002:164c` — NootedRed obligatorio |
| RAM | 16 GB DDR4 |
| NVMe | Kingston NV3 (DRAM-less) |
| Audio | Realtek ALC236 (alcid=13) |
| Pantalla | eDP 1366×768 interno |
| Teclado | PS/2 (`\_SB.PCI0.SBRG.PS2K`, `_HID=HPQ8001`, `_CID=PNP0303`) |
| Touchpad | ELAN0708 I2C (`\_SB.I2CD.TPD0`, `_CID=PNP0C50`, GPIO pin 9) |
| BIOS | F.30 (AMI) — sin Above 4G Decoding accesible |
| OpenCore | 1.0.7 |
| macOS objetivo | Ventura 13 |

## Estado actual (2026-06-02) — FUNCIONAL

- **macOS Ventura 13 INSTALADO** en HDD (`sda2`, APFS), arranca del disco interno **sin USB**. ✓
- **iGPU acelerada**: 2 GB VRAM, Metal 3 (NootedRed v0.8.10). ✓
- **Brillo** ✓ (vía `AMDBacklight=1`: NootedRed trata iMac20,1 como desktop sin ese arg).
- **Audio** (alcid=13) ✓ · **Batería** ✓ · **Teclado/touchpad** internos ✓.
- Copiar el EFI al disco interno: usar **MountEFI** (chris1111), NO `cp EFI sobre sí misma`.
- **Versión: quedarse en Ventura** (Sonoma lateral, Sequoia experimental).
- **Pendiente:** WiFi (dongle USB, no soportado), USB mapping real (USBToolBox), limpiar `-v debug`.

## Gotchas confirmados (NO cambiar sin leer)

| Problema | Fix | Por qué |
|---|---|---|
| Cpuid1Data/Mask no vacíos | Dejar vacíos | Spoof Intel encima de AMD_Vanilla → panic negro |
| Booter Quirks modernos | Usar esquema moderno (Otus9051) | El legacy colgaba en ExitBootServices tras alinear SSDTs |
| SSDT-PLUG Intel | Usar SSDT-PLUG-ALT | Intel PLUG busca P001/P002 → AE_NOT_FOUND; AMD solo tiene P000 |
| AMDRyzenCPUPowerManagement v0.7.2 | OFF + DummyPM=True | Caps Lock on (kernel panic) en esta config |
| npci=0x3000 | Siempre en boot-args | BIOS HP sin Above 4G Decoding |
| SMBIOS MacBookPro16,3 | Usar iMac20,1 | ChefKiss: crash framebuffer NootedRed en 16,3 |
| AmdTscSync | Usar ForgedInvariant v1.5.0 | TSC desincronizado → cuelgue en AppleKeyStore |
| BOOTx64.efi = copia de OpenCore.efi | Bootstrap de 24KB | Mismo tamaño → "failed to load configuration" |
| LauncherOption=Full | LauncherOption=Disabled | Entrada NVRAM autorreferencial → bucle StartImage |

## Perfiles de EFI

Un solo árbol de kexts/SSDTs; 3 `config.plist` en `EFI/OC/profiles/` (el activo es `EFI/OC/config.plist`):
- `--profile install` → USB instalador (verbose+debug, UTBDefault).
- `--profile stable` → = el EFI que arranca hoy (ancla anti-regresión; default).
- `--profile postinstall` → uso diario (sin debug, Timeout=5, +ECEnabler +SSDT-RTCAWAC, ApfsTrim=0 HDD, UTBMap si existe).
- `--all` → genera los 3, deja `stable` activo.

SystemUUID/ROM están **fijos** (constantes) — no se regeneran en cada run. AMD PM se queda OFF en los 3.

## Flujo de trabajo estándar

```bash
cd macos

# 1. Editar el generador si hace falta (fuente de verdad)
nano scripts/05_generate_config.py

# 2. Regenerar el perfil deseado (hace backup automático)
python3 scripts/05_generate_config.py --profile postinstall

# 3. Validar (siempre antes de sync)
./tools/ocvalidate ./EFI/OC/config.plist   # debe decir "No issues found"

# 4a. USB: sincronizar (perfil install). SYNC_FAST=1 sin audios
SYNC_FAST=1 ./scripts/06_sync_usb_efi.sh
# 4b. Disco interno: MountEFI → reemplazar config.plist en el ESP → Reset NVRAM

# 5. Arrancar desde puerto USB 2.0 (negro)
```

## Toggles del generador (`05_generate_config.py`)

| Toggle | Default | Efecto |
|---|---|---|
| `USE_NRED_DP_DELAY` | True | Añade `-NRedDPDelay` (fix eDP link-training Lucienne) |
| `USE_NRED_NO_ACCEL` | False | Añade `-NRedNoAccel` (framebuffer sin Metal, para aislar) |
| `USE_I2C_POLLING` | True | Añade `voodooI2CPoling=1` (touchpad sin GPIO) |
| `USE_MINIMAL_ACPI_FOR_FB_TEST` | False | 6 SSDTs mínimos en lugar de 11 |

## Kexts activos ahora

| Kext | Estado | Motivo |
|---|---|---|
| Lilu | ON | Base |
| VirtualSMC | ON | SMC |
| ForgedInvariant v1.5.0 | ON | TSC sync AMD |
| NootedRed v0.8.10 | ON | iGPU Vega 6 — obligatorio desde instalación |
| AppleMCEReporterDisabler | ON | Evita panic AMD multi-socket |
| AppleALC | ON | Audio ALC236 |
| RestrictEvents | ON | SMBIOS iMac20,1 |
| NVMeFix | ON | Kingston NV3 |
| VoodooI2C v2.9.1 | ON | Bus I2C para touchpad ELAN0708 |
| VoodooI2CHID | ON | Dispositivo HID I2C (PNP0C50) |
| VoodooPS2Controller | ON | Teclado PS/2 |
| USBToolBox + UTBDefault | ON | USB mapping |
| SMCBatteryManager | ON | Batería |
| SMCLightSensor / SMCSuperIO | ON | Sensores |
| BrightnessKeys | ON | Fn+brillo |
| **AMDRyzenCPUPowerManagement** | **OFF** | Kernel panic (Caps Lock on) |
| **SMCAMDProcessor** | **OFF** | Depende del anterior |

## SSDTs activos (11)

`SSDT-ALS0`, `SSDT-EC`, `SSDT-GPRW`, `SSDT-HPET`, `SSDT-PLUG-ALT`, `SSDT-PMC`, `SSDT-PNLF`, `SSDT-PS2K`, `SSDT-USBX`, `SSDT-XOSI`, `SSDT-USB-Reset`

Fuentes en `macos/acpi_src/`. Compilar con `iasl` si editas un `.dsl`.

## EFIs de referencia

| Repo | Qué es | Dónde |
|---|---|---|
| hp-245-g8-efi-base | **Mismo modelo exacto** — SSDTs reales del equipo | `docs/hp-245-g8-efi-base/` |
| otus9051-hp15s | **Mismo CPU exacto** (5300U) — arranca con HDMI | `docs/otus9051-hp15s/` |

Ambas tienen su propio `.git` — no modificar como parte de este repo.

## Skills adicionales disponibles

- `diagnose-boot.md` — checklist síntoma → causa → fix
- `read-oc-log.md` — cómo leer el log de OpenCore del USB
- `regen-config.md` — pasos detallados para regenerar config
- `sync-efi.md` — opciones del script de sincronización

## Próximos pasos (problemas abiertos)

1. **Teclado/touchpad** — investigación en curso (workflow en ejecución)
2. **Instalar macOS** — una vez funcione el input (o con teclado USB externo)
3. **AMDRyzenCPUPowerManagement** — re-evaluar tras instalar con sistema estable
4. **NootedRed nightly** — considerar si 0.8.10 release tiene problemas de eDP
