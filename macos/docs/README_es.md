# Hackintosh EFI — Ryzen 3 5300U (Renoir)

## Hardware detectado

| Componente   | Detalle                                    |
|-------------|--------------------------------------------|
| CPU         | AMD Ryzen 3 5300U (4C/8T, Zen 2, Lucienne/Renoir) |
| WiFi        | Realtek RTL8822CE `[10ec:c822]`            |
| Arquitectura| x86_64                                     |
| Host OS     | Arch Linux (Omarchy)                       |

## SMBIOS objetivo

- **Modelo**: MacBookPro16,3
- **macOS**: 14 Sonoma (Mac-937A206F2EE63C01)

## Estructura del proyecto

```
Dev/macos/
├── run.sh                    ← Script principal (menú interactivo)
├── scripts/
│   ├── 01_install_ocat.sh    ← Instalar OCAT + dependencias
│   ├── 02_download_recovery.sh← Descargar macOS Sonoma Recovery
│   ├── 03_download_kexts.sh  ← Descargar los kexts necesarios
│   └── 04_generate_config.sh ← Guía interactiva OCAT paso a paso
├── kexts/                    ← Kexts descargados
├── recovery/                 ← Archivos BaseSystem.dmg + .chunklist
├── EFI/                      ← EFI generada por OCAT (después del paso 4)
├── docs/                     ← Documentación y notas
└── tools/                    ← OpenCorePkg (clonado por script 02)
```

## Uso rápido

```bash
# Ejecutar todo en orden automático
bash run.sh
# Elegir opción 5

# O paso a paso:
bash scripts/01_install_ocat.sh
bash scripts/02_download_recovery.sh
bash scripts/03_download_kexts.sh
bash scripts/04_generate_config.sh
```

## Kexts incluidos

| Kext              | Función                          |
|-------------------|----------------------------------|
| Lilu.kext          | Base para todos los kexts       |
| VirtualSMC.kext    | Emula SMC de Apple              |
| NootedRed.kext     | Gráficos AMD (Cézanne/Renoir)  |
| AppleALC.kext      | Audio HD                        |
| USBToolBox.kext    | Mapeo de puertos USB            |
| VoodooPS2Controller | Teclado + Trackpad              |
| SMCBatteryManager  | Estado de batería               |
| NVMeFix.kext       | Optimización NVMe               |
| BrightnessKeys.kext| Teclas de brillo                |
| AMDTscSync.kext    | Sincronización TSC (AMD CPU)    |
| RestrictEvents.kext| Bloqueo de procesos no soportados|

## Ajustes de BIOS/UEFI requeridos

- Disable Secure Boot
- Disable Fast Boot
- Enable Above 4G Decoding
- Set UEFI boot mode
- Disable CSM (Compatibility Support Module)

## Notas importantes

- **NootedRed** reemplaza a WhateverGreen. NO usar ambas.
- El WiFi RTL8822CE no funciona en macOS. Ver `docs/wifi_rtl8822ce.md`
- El archivo `config.plist` se genera con OCAT (paso 4).
  No lo edites manualmente a menos que sepas lo que haces.
