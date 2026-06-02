---
name: sync-efi
description: Sincroniza EFI/ al USB pendrive con label MACOS
---
Sincroniza la carpeta EFI al USB instalador de macOS.

## Uso
```bash
cd /home/jemg/Dev/hp-245-g8-jemg/macos
# Sync completo (incluye Audio ~360 mp3):
./scripts/06_sync_usb_efi.sh
# Sync rápido (excluye Audio para iterar rápido):
SYNC_FAST=1 ./scripts/06_sync_usb_efi.sh
# Si necesitas override del label del USB:
USB_LABEL=MYUSB ./scripts/06_sync_usb_efi.sh
# Con sudo (emergencia):
FORCE_SUDO=1 ./scripts/06_sync_usb_efi.sh
```
## Notas
- USB debe tener label MACOS
- Usa puerto USB 2.0 (negro) siempre
- Requiere udisksctl (no ejecutar como root)
