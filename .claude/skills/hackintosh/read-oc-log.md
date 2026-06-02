---
name: read-oc-log
description: Lee los logs de arranque de OpenCore desde la ESP del USB
---
Lee los logs de OpenCore grabados durante el arranque.

## Uso
```bash
# Montar ESP del USB (label MACOS):
udisksctl mount -b /dev/disk/by-label/MACOS
# Ver logs (ajusta la ruta según donde monte):
ls /run/media/$USER/MACOS/EFI/OC/
# Leer el log más reciente:
ls -t /run/media/$USER/MACOS/*.txt | head -1 | xargs cat
# O buscar todos los .txt:
find /run/media/$USER/MACOS/ -name "*.txt" -newer /run/media/$USER/MACOS/EFI/OC/config.plist
```
## Prefijos importantes en los logs
- BS: = Boot Services (fase pre-OS)
- OC: = OpenCore loader
- OCB: = OpenCore boot manager
- OCABC: = Apple Boot Compat (Booter)
