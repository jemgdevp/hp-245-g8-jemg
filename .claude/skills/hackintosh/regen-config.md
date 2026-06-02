---
name: regen-config
description: Regenera config.plist desde el script generador y valida
---
Regenera EFI/OC/config.plist desde el generador Python.

## Uso
```bash
cd /home/jemg/Dev/hp-245-g8-jemg/macos
# Regenerar (hace backup automático con hash):
python3 scripts/05_generate_config.py
# Validar con ocvalidate:
./tools/ocvalidate ./EFI/OC/config.plist
# Ciclo completo (regen + validar + sync):
python3 scripts/05_generate_config.py && ./tools/ocvalidate ./EFI/OC/config.plist && ./scripts/06_sync_usb_efi.sh
```
## Toggles del generador (editar en scripts/05_generate_config.py)
- USE_NRED_DP_DELAY (~línea 90): añade -NRedDPDelay a boot-args
- USE_MINIMAL_ACPI_FOR_FB_TEST (~línea 221): set ACPI mínimo vs completo
