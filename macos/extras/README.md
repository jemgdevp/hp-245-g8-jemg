# extras/ — kexts que NO van por OpenCore

Kexts que **no** se inyectan desde `EFI/OC/Kexts` ni se declaran en `config.plist`, sino que se
instalan dentro de macOS en `/Library/Extensions/` (`/L/E`). No los añadas al generador.

## AMDMicrophone.kext (micrófono interno digital)

Habilita el **micrófono interno** (Audio Co-Processor / ACP) de los laptops Renoir/Lucienne. NootedRed
da salida de audio (vía AppleALC) pero NO el micro digital interno; ese lo aporta AMDMicrophone.

**No carga por OpenCore** (depende de `IOAudioFamily`, que carga tarde) → va en `/L/E`.

### Requisitos
- SIP debe permitir kexts sin firmar. **Ya cumplido**: nuestro `csr-active-config=03080000` incluye
  el bit `CSR_ALLOW_UNTRUSTED_KEXTS` (0x1). No hace falta cambiarlo. (El mínimo que pide el proyecto
  es `csr=01000000`; el nuestro es menos restrictivo y ya lo cubre.)

### Instalación (en macOS, una sola vez)
```bash
# 1. Copiar el kext a /Library/Extensions
sudo cp -R /ruta/a/extras/AMDMicrophone.kext /Library/Extensions/

# 2. Permisos correctos
sudo chown -R root:wheel /Library/Extensions/AMDMicrophone.kext
sudo chmod -R 755 /Library/Extensions/AMDMicrophone.kext

# 3. Reconstruir la caché de kexts
sudo kmutil install --volume-root / --update-all     # Ventura/Sonoma
#   (en versiones viejas: sudo kextcache -i /)

# 4. Reiniciar
sudo reboot
```

### Verificación
```bash
kmutil showloaded | grep -i AMDMicrophone     # debe aparecer com.qhuyduong.AMDMicrophone
# y en Ajustes > Sonido > Entrada debe salir el micrófono interno
```

### Notas
- Si macOS bloquea el kext ("se bloqueó la extensión del sistema"), aprobarlo en
  Ajustes > Privacidad y seguridad, o verificar el SIP.
- Es **solo el micrófono interno**. AppleALC sigue siendo necesario para los altavoces/jack.
- Versión incluida: AMDMicrophone v1.0.0 (qhuyduong). Repo: https://github.com/qhuyduong/AMDMicrophone
