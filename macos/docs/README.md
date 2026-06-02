# Hackintosh EFI — HP 245 G8 (Ryzen 3 5300U / Renoir) + NootedRed

> Documentación de la carpeta `macos/`. El README principal del proyecto está en la **raíz** del repo.
> Estado: **macOS Ventura 13 instalado y funcional** (iGPU acelerada, brillo, audio, batería, sin USB).

## Hardware

| Componente   | Detalle                                             |
|-------------|------------------------------------------------------|
| CPU         | AMD Ryzen 3 5300U (4C/8T, Zen 2, Lucienne/Renoir)    |
| iGPU        | AMD Vega 6 `[1002:164c]` — NootedRed (acelerada, Metal 3) |
| Audio       | Realtek ALC236 (`alcid=13`)                          |
| WiFi        | Realtek RTL8822CE `[10ec:c822]` — **no soportado en macOS** |
| Almacenam.  | HDD WDC 500 GB (macOS) + NVMe Kingston (Arch Linux)  |
| Host OS     | Arch Linux (Omarchy)                                 |

## SMBIOS y macOS

- **SMBIOS**: `iMac20,1` (recomendado por ChefKiss para NootedRed en Renoir/Lucienne).
- **macOS**: Ventura 13 (instalado). Decisión: **quedarse en Ventura** — Sonoma es lateral
  (crashes propios de NootedRed) y Sequoia experimental; nada de lo que falta mejora al subir.

## Estructura del proyecto

```
macos/
├── scripts/
│   ├── 01_install_ocat.sh      ← Instalar OCAT + dependencias (uso único)
│   ├── 02_download_recovery.sh ← Descargar macOS Recovery (Ventura)
│   ├── 03_download_kexts.sh    ← Descargar kexts a kexts/
│   ├── 04_generate_config.sh   ← Guía OCAT legacy (OBSOLETO)
│   ├── 05_generate_config.py   ← FUENTE DE VERDAD del config.plist
│   ├── 06_sync_usb_efi.sh      ← Sincroniza EFI/ al USB (sin sudo, udisksctl)
│   └── 07_rebuild_usb.sh       ← Reconstruye el USB desde cero (wipefs + GPT + FAT32 + EFI)
├── EFI/                        ← El "producto": EFI de OpenCore que va al USB / disco interno
├── acpi_src/                   ← Fuentes .dsl de los SSDTs (compilar con iasl → .aml)
├── recovery_ventura/           ← BaseSystem.dmg + chunklist del Recovery
├── tools/                      ← ocvalidate, OpenCorePkg, AMD_Vanilla
└── docs/                       ← Esta doc, DIAGNOSTICO.md (bitácora), DSDT, EFIs de referencia
```

## Flujo de trabajo (editar → generar → validar → sincronizar)

```bash
cd macos
# 1. Editar toggles/valores en el generador (fuente de verdad)
nano scripts/05_generate_config.py
# 2. Regenerar config.plist (hace backup automático)
python3 scripts/05_generate_config.py
# 3. Validar SIEMPRE antes de sincronizar
./tools/ocvalidate ./EFI/OC/config.plist     # debe decir "No issues found"
# 4. Sincronizar al USB (label MACOS)
./scripts/06_sync_usb_efi.sh
```

Para reconstruir el USB desde cero (otro pendrive o uno corrupto): `sudo ./scripts/07_rebuild_usb.sh /dev/sdX`.
Para copiar el EFI al disco interno desde macOS: usar **MountEFI** (chris1111). Ver README de la raíz.

## Kexts principales (estado actual)

| Kext                       | Estado | Función                                  |
|----------------------------|--------|------------------------------------------|
| Lilu                       | ON     | Base de todos los kexts                  |
| VirtualSMC                 | ON     | Emula el SMC de Apple                    |
| ForgedInvariant v1.5.0     | ON     | Sincronización TSC (AMD) — NO AmdTscSync |
| NootedRed v0.8.10          | ON     | iGPU Vega 6 (acelerada, Metal 3)         |
| AppleALC                   | ON     | Audio ALC236 (`alcid=13`)                |
| RestrictEvents             | ON     | SMBIOS iMac20,1 + `revblock=media`       |
| NVMeFix                    | ON     | Optimización NVMe                        |
| VoodooPS2Controller (+plugins) | ON | Teclado interno                          |
| VoodooI2C (+plugins) / VoodooI2CHID | ON | Touchpad ELAN (I2C)                  |
| USBToolBox + UTBDefault    | ON     | Mapeo USB (UTBDefault es provisional)    |
| SMCBatteryManager          | ON     | Estado de batería                        |
| BrightnessKeys / SMCLightSensor | ON | Teclas y slider de brillo               |
| AppleMCEReporterDisabler   | ON     | Evita panic AMD (codeless)               |
| **AMDRyzenCPUPowerManagement** | **OFF** | Causa kernel panic en esta config    |
| **SMCAMDProcessor**        | **OFF** | Depende del anterior                     |

## Notas importantes

- **NootedRed reemplaza a WhateverGreen** — NO usar ambos (este EFI NO lleva WhateverGreen).
- **NootedRed va HABILITADO desde la instalación** (Renoir no tiene framebuffer básico sin él).
  Durante la fase de copia se puede añadir `-NRedNoAccel` *manual en el picker* si la pantalla
  se congela; NO va en el config.
- **Brillo**: requiere `AMDBacklight=1` en boot-args porque con SMBIOS `iMac20,1` (sin "Book")
  NootedRed trata el equipo como desktop y no registra el backlight.
- **`config.plist` se genera con `05_generate_config.py`** — no lo edites a mano; edita el generador.
- **WiFi RTL8822CE** no funciona en macOS. Ver `wifi_rtl8822ce.md`.
- Bitácora completa de diagnóstico y decisiones: `DIAGNOSTICO.md`.
