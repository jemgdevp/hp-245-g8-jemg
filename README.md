# Hackintosh — HP 245 G8 (Ryzen 3 5300U / Lucienne) + NootedRed

> **Objetivo actual**: Instalar macOS Ventura en el HP 245 G8 y completar la post-instalación (teclado/touchpad PS2, audio, USB mapping).

## Hardware

| Componente     | Detalle                                      |
|----------------|----------------------------------------------|
| Modelo         | HP 245 G8 Notebook PC                        |
| CPU            | AMD Ryzen 3 5300U (4C/8T, Zen 2, Lucienne)   |
| iGPU           | AMD Lucienne [1002:164c] (Vega 6)            |
| RAM            | 16 GB DDR4                                   |
| Almacenamiento | Kingston NV3 NVMe (DRAM-less)                |
| WiFi           | Realtek RTL8822CE (sin soporte nativo)       |
| Audio          | Realtek ALC236                               |
| BIOS           | F.30 (AMI)                                   |
| Pantalla       | eDP 1366x768 (interno)                       |

**Notas importantes de hardware**:
- WiFi no funciona en macOS → usar dongle USB-Ethernet (RTL8153 recomendado).
- VRAM subida a **2 GB** en BIOS (crítico para NootedRed).
- No tiene Above 4G Decoding fácil → usamos `npci=0x3000`.

## Estado actual — macOS Ventura FUNCIONAL (2026-06-02)

**HITO ALCANZADO**: macOS Ventura 13 instalado en el HDD interno (`sda2`, APFS), arrancando
desde el EFI del disco interno (`sda1`) **sin la USB**, con lo esencial funcionando. Dual boot
con Arch Linux (NVMe) intacto.

**Funciona:**
- ✅ **iGPU acelerada**: AMD Radeon RX Renoir Graphics, **VRAM 2 GB, Metal 3** (NootedRed v0.8.10).
- ✅ **Brillo** del panel interno (slider + teclas) — vía `AMDBacklight=1` (ver nota abajo).
- ✅ **Audio** (ALC236, `alcid=13`).
- ✅ **Batería** (lectura correcta de carga/estado, SMCBatteryManager).
- ✅ **Teclado y touchpad** internos (sub-plugins PS2/I2C + parche `_OSI→XOSI`).
- ✅ Arranque desde disco interno sin USB.

**Pendiente / limitaciones conocidas:**
- ⚠️ **WiFi RTL8822CE** no soportado en macOS → usar dongle USB. Ver `macos/docs/wifi_rtl8822ce.md`.
- ⚠️ **USB mapping** real (reemplazar `UTBDefault` por mapa propio con USBToolBox).
- ⚠️ Limitaciones permanentes de NootedRed: sin decodificación HW de vídeo (VCN/DRM), sin audio HDMI, sleep/wake no fiable.
- 🔧 Limpieza opcional: quitar `-v debug=0x100 keepsyms=1` de boot-args para uso diario.

> **El slider de brillo y NootedRed:** NootedRed solo activa el backlight si Lilu detecta "laptop",
> y Lilu lo decide buscando "Book" en el SMBIOS. Con `iMac20,1` (sin "Book") el backlight queda
> desactivado pese a acelerar bien. Fix: `AMDBacklight=1` en boot-args (override del propio kext).

> **Decisión de versión:** quedarse en **Ventura**. Sonoma es lateral (crashes propios de NootedRed)
> y Sequoia es experimental; nada de lo que falta mejora al subir. Ver `macos/docs/DIAGNOSTICO.md`.

### Config que funciona (estado actual del EFI)

| Parametro | Valor |
|---|---|
| macOS | Ventura 13 — instalado en `sda2` (APFS) |
| iGPU | NootedRed v0.8.10 — acelerada (2 GB VRAM, Metal 3) |
| Brillo | `AMDBacklight=1` (NootedRed trata iMac20,1 como desktop sin este arg) |
| AMDRyzenCPUPowerManagement | DESHABILITADO (causa kernel panic) |
| SMCAMDProcessor | DESHABILITADO (depende del anterior) |
| DummyPowerManagement | True |
| TSC sync | ForgedInvariant v1.5.0 |
| SSDT CPU | SSDT-PLUG-ALT.aml (version AMD) |
| Booter/Kernel quirks | `DevirtualiseMmio`/`ProtectUefiServices`/`DisableIoMapper`/`LapicKernelPanic` = False (alineado Otus9051) |
| boot-args | `-v keepsyms=1 debug=0x100 npci=0x3000 alcid=13 agdpmod=pikera revblock=media AMDBacklight=1 -NRedDPDelay` |
| SMBIOS | iMac20,1 |

## USB instalador — qué lleva y cómo recrearlo desde cero

### Qué está en el USB ahora

```
USB: FAT32, GPT, etiqueta MACOS (~7.5 GB con LED de actividad)
│
├── com.apple.recovery.boot/
│   ├── BaseSystem.dmg        ← Recovery macOS Ventura 13 (674 MB)
│   └── BaseSystem.chunklist
│
└── EFI/
    ├── BOOT/
    │   └── BOOTx64.efi       ← Bootstrap de OpenCore (NO copiar OpenCore.efi aquí)
    └── OC/
        ├── config.plist      ← Config generado (fuente de verdad: scripts/05_generate_config.py)
        ├── OpenCore.efi
        ├── ACPI/             ← 10 SSDTs (ver lista abajo)
        ├── Drivers/          ← HfsPlus.efi, OpenRuntime.efi
        ├── Kexts/            ← 18 kexts (NootedRed, Lilu, ForgedInvariant v1.5.0, etc.)
        └── Tools/            ← CleanNvram.efi
```

**SSDTs activos** (en config.plist — el .aml debe existir en ACPI/):

| Archivo | Para qué sirve |
|---|---|
| SSDT-ALS0.aml | Sensor de luz falso (evita panic por ALS ausente) |
| SSDT-EC.aml | Controlador EC (path `\_SB.PC00.SBRG.EC0` real de este HP) |
| SSDT-GPRW.aml | Fix instant-wake (parche GPRW→XPRW) |
| SSDT-HPET.aml | Fix conflictos IRQ HPET |
| SSDT-PLUG-ALT.aml | Plugin-type para CPU (version AMD — no la estandar Intel) |
| SSDT-PNLF.aml | Brillo del panel |
| SSDT-PMC.aml | Fix PMC |
| SSDT-USB-Reset.aml | Reset RHUB para USB (XHC0, XHC1) |
| SSDT-USBX.aml | USBX power properties |
| SSDT-XOSI.aml | Fingir Windows para ACPI |

**Kexts habilitados / deshabilitados ahora mismo:**

| Kext | Estado | Motivo |
|---|---|---|
| Lilu | ON | Base |
| VirtualSMC | ON | SMC |
| ForgedInvariant v1.5.0 | ON | TSC sync AMD |
| NootedRed v0.8.10 | ON | iGPU Vega 6 |
| AppleMCEReporterDisabler | ON | Evita panic AMD multi-socket |
| AppleALC | ON | Audio alcid=13 |
| RestrictEvents | ON | SMBIOS iMac20,1 |
| NVMeFix | ON | Kingston NV3 |
| VoodooPS2Controller (+plugins) | ON | Teclado interno (funciona) |
| VoodooI2C (+plugins) / VoodooI2CHID | ON | Touchpad ELAN I2C (funciona) |
| BrightnessKeys | ON | Fn+brillo |
| USBToolBox + UTBDefault | ON | USB mapping |
| SMCBatteryManager | ON | Bateria |
| SMCLightSensor / SMCSuperIO | ON | Sensores |
| **AMDRyzenCPUPowerManagement** | **OFF** | Causa kernel panic en esta config |
| **SMCAMDProcessor** | **OFF** | Depende del anterior |

**Boot args actuales:** `-v keepsyms=1 debug=0x100 npci=0x3000 alcid=13 -NRedDPDelay`

**DummyPowerManagement:** `True` (mientras AMD PM kexts estén OFF)

---

### Recrear el USB desde cero

Si necesitas formatear otro USB (o el actual está corrupto):

```bash
# 1. Identificar el dispositivo (busca tu USB por tamaño/etiqueta/modelo)
lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT,MODEL
# Confirma que /dev/sdX es el USB (modelo "UDisk", ~8GB), NO el HDD (WDC) ni el NVMe (KINGSTON).

# 2. Desmontar si está montado
udisksctl unmount -b /dev/sdX1 2>/dev/null; true

# 3. SUDO — LIMPIAR firmas residuales (¡crítico!). Un USB que antes fue de Debian/otra
#    distro deja una firma iso9660 híbrida que confunde al firmware HP. wipefs la borra.
sudo wipefs -a /dev/sdX

# 4. SUDO — crear tabla GPT + partición FAT32 (¡borra todo!)
sudo parted /dev/sdX --script mklabel gpt mkpart primary fat32 1MiB 100%
sudo partprobe /dev/sdX; sleep 2
sudo mkfs.vfat -F 32 -n MACOS /dev/sdX1

# 5. Montar (sin sudo)
udisksctl mount -b /dev/sdX1

# 6. Copiar recovery + EFI (desde la raíz del repo, sin sudo)
#    IMPORTANTE: usar cp, NO `rsync -a` — FAT32 no soporta chown y rsync -a falla
#    ("chown ... Operation not permitted"). Copiar solo los .aml de ACPI (los .dsl
#    son fuentes y no se cargan).
MP="/run/media/$USER/MACOS"
mkdir -p "$MP/com.apple.recovery.boot"
cp macos/recovery_ventura/com.apple.recovery.boot/BaseSystem.dmg       "$MP/com.apple.recovery.boot/"
cp macos/recovery_ventura/com.apple.recovery.boot/BaseSystem.chunklist "$MP/com.apple.recovery.boot/"

mkdir -p "$MP/EFI/BOOT" "$MP/EFI/OC/ACPI" "$MP/EFI/OC/Drivers" "$MP/EFI/OC/Kexts" "$MP/EFI/OC/Tools"
cp macos/EFI/OC/ACPI/*.aml      "$MP/EFI/OC/ACPI/"
cp -r macos/EFI/OC/Drivers/.    "$MP/EFI/OC/Drivers/"
cp -r macos/EFI/OC/Kexts/.      "$MP/EFI/OC/Kexts/"
cp -r macos/EFI/OC/Tools/.      "$MP/EFI/OC/Tools/"
cp macos/EFI/OC/OpenCore.efi    "$MP/EFI/OC/"
cp macos/EFI/OC/config.plist    "$MP/EFI/OC/"
cp macos/EFI/BOOT/BOOTx64.efi   "$MP/EFI/BOOT/"
sync

# 7. Validar (debe decir "No issues found")
macos/tools/ocvalidate "$MP/EFI/OC/config.plist"

# 8. Verificar integridad
md5sum macos/EFI/OC/config.plist "$MP/EFI/OC/config.plist"
cmp macos/recovery_ventura/com.apple.recovery.boot/BaseSystem.dmg "$MP/com.apple.recovery.boot/BaseSystem.dmg" && echo "DMG OK"
```

> **Atajo:** los scripts `/tmp/rebuild_usb.sh` (formatea) + `/tmp/finish_usb.sh` (copia EFI con `cp`)
> automatizan todo esto con guardas de seguridad (verifican tamaño/modelo antes de borrar) y todas
> las validaciones. Se usaron en la reconstrucción del 2026-06-01.

> **Notas criticas:**
> - `BOOTx64.efi` debe ser el **Bootstrap** (~24 KB), NO una copia de `OpenCore.efi` (~626 KB). Si los tamaños son iguales algo está mal.
> - **`wipefs -a` antes de particionar** — si no, una firma iso9660 residual (ej. de un USB que antes fue de Debian) sobrevive y puede confundir al firmware HP.
> - **`cp`, nunca `rsync -a`** sobre el USB — FAT32 no soporta ownership Unix.
> - **`mkfs.vfat` cambia el UUID de la partición.** Eso invalidaba entradas NVRAM viejas del firmware HP, pero NO rompe el arranque porque `BOOTx64.efi` (Bootstrap) arranca por el path de fallback `\EFI\BOOT\BOOTx64.efi` (independiente del UUID) y `LauncherOption=Disabled` evita la entrada NVRAM autorreferencial.
> - **No regenerar `config.plist` solo para reconstruir el USB:** el generador asigna un `SystemUUID`/`ROM` nuevos en cada run. Usa el `config.plist` ya existente para mantener el SMBIOS estable.
> - Usar siempre un puerto **USB 2.0 (negro)** al arrancar en el HP 245 G8.
> - El recovery en `macos/recovery_ventura/` se descargó con `scripts/02_download_recovery.sh`. Si se pierde, volver a ejecutarlo (necesita internet).

---

## Post-instalación — copiar el EFI al disco interno (arrancar sin USB)

Una vez macOS está instalado y arranca (todavía con la USB), hay que copiar la carpeta `EFI/`
al ESP del disco interno para poder quitar la USB. **Desde macOS** el método recomendado es
**MountEFI** de chris1111 (app gráfica que monta cualquier partición EFI):
<https://github.com/chris1111/MountEFI>

> ⚠️ **NO** uses `sudo cp -R /Volumes/EFI/EFI /Volumes/EFI/` — copia la EFI sobre sí misma.
> Hay **dos** particiones EFI (la de la USB y la del disco interno) y macOS las monta como
> `/Volumes/EFI` y `/Volumes/EFI 1`; hay que distinguirlas bien.

Pasos:

1. Arranca macOS **con la USB puesta**.
2. Abre **MountEFI** → monta el ESP del **disco interno** (HDD WDC, `disk0s1` normalmente).
   Vuelve a abrirlo y monta también el ESP de la **USB**. Verás dos volúmenes EFI en Finder.
3. Identifica cuál es cuál (la de la USB ya tiene una carpeta `EFI/` con OpenCore; la del
   disco interno suele estar vacía o con un EFI mínimo del firmware).
4. Copia la carpeta `EFI` **de la USB** → al **ESP del disco interno**.
5. Verifica que en el disco interno quede `EFI/OC/config.plist`, `EFI/OC/OpenCore.efi` y
   `EFI/BOOT/BOOTx64.efi` (este último ~24 KB, el Bootstrap).
6. Apaga, quita la USB, enciende: debe aparecer el picker de OpenCore desde el disco interno.

> Alternativa por Terminal (con cuidado de no confundir los dos volúmenes EFI):
> ```bash
> diskutil list                 # identifica disk0s1 (interno) vs el ESP de la USB
> sudo diskutil mount disk0s1   # ESP del disco interno
> # copia desde el EFI de la USB (p.ej. "/Volumes/EFI 1/EFI") al interno ("/Volumes/EFI"):
> sudo rm -rf /Volumes/EFI/EFI && sudo cp -R "/Volumes/EFI 1/EFI" /Volumes/EFI/
> ```

---

## Uso rápido (generar + sincronizar)

```bash
cd macos

# 1. Edita los toggles según el test que quieras hacer
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

## Perfiles de EFI (install / stable / postinstall)

El generador produce 3 perfiles sobre **un solo árbol de kexts/SSDTs** (no duplica carpetas).
Cada uno es un `config.plist` distinto guardado en `EFI/OC/profiles/`; el activo (`EFI/OC/config.plist`)
es el que sincroniza `06_sync_usb_efi.sh`.

```bash
cd macos
python3 scripts/05_generate_config.py --profile install      # USB instalador
python3 scripts/05_generate_config.py --profile postinstall  # uso diario (disco interno)
python3 scripts/05_generate_config.py --profile stable       # = el EFI que arranca hoy (ancla)
python3 scripts/05_generate_config.py --all                  # genera los 3; deja 'stable' activo
```

| Clave | install | stable (=actual) | postinstall |
|---|---|---|---|
| boot-args debug (`-v keepsyms=1 debug=0x100`) | sí | sí | **no** |
| Misc>Debug Target | 67 (log a ESP) | 67 | 3 (sin log) |
| DisableWatchDog | sí | sí | no |
| Boot Timeout | 0 (espera) | 0 | 5 (auto-arranca) |
| USB | UTBDefault | UTBDefault | **UTBMap** (si existe) |
| Extra kexts/SSDT | — | — | **ECEnabler + RealtekRTL8111 + SMCProcessorAMD + SMCRadeonSensors + SSDT-RTCAWAC** |
| Quita kexts | — | — | **SMCSuperIO** (no va en AMD) **+ AppleALCU** (no carga en Ventura) |
| Extra boot-args | — | — | **revpatch=cpuname** (nombre real del CPU) |

> **Sensores (postinstall):** `SMCProcessorAMD` (macos86, temperatura CPU) y `SMCRadeonSensors`
> (temperatura iGPU) son solo informativos (iStat/Macs Fan Control); no tocan power management.
> Se usa el fork **macos86** de SMCProcessorAMD (standalone), NO el de trulyspinach (que arrastra
> AMDRyzenCPUPowerManagement → panic).
>
> **Micrófono interno:** `AMDMicrophone.kext` está en `macos/extras/` — se instala en
> `/Library/Extensions/` (NO por OpenCore). Ver `macos/extras/README.md`.
| SetApfsTrimTimeout | -1 | -1 | **0** (HDD sin TRIM) |
| AMD PM kexts | OFF | OFF | OFF (ver nota) |

Invariantes (idénticos en los 3): SMBIOS iMac20,1, NootedRed, parches AMD_Vanilla (cores=4),
quirks alineados a Otus9051, input (PS2+I2C), `AMDBacklight=1`, SystemUUID/ROM **fijos**.

## Pendientes (post-instalación)

1. **USB mapping real** — generar `UTBMap.kext` con USBToolBox/USBMap **desde macOS** (enchufando
   en cada puerto físico) y dejarlo en `EFI/OC/Kexts/`; el perfil `postinstall` lo usa automáticamente.
2. **AMD CPU PM** — se queda **OFF**. No es problema de versión: esos kexts escriben P-states legacy
   por MSR sin CPPC, que es justo lo que la APU Lucienne móvil usa → cuelgan/paniquean. El SMU del
   firmware ya gobierna frecuencia/voltaje con `DummyPowerManagement=True`. (Opcional: `SMCProcessorAMD`
   solo-sensores para ver temperaturas, sin tocar PM.)
3. **WiFi RTL8822CE** — sin soporte nativo en macOS; usar dongle USB. Ver `macos/docs/wifi_rtl8822ce.md`.
4. **Migrar a SSD/NVMe** (opcional) — macOS está en HDD WD (funciona, pero lento). El NVMe actual es
   de Arch (no tocar); requeriría otro disco.

### Ya funcionando ✅

iGPU acelerada (2 GB VRAM, Metal 3) · **teclado interno** · **touchpad** · brillo · audio (alcid=13)
· batería · arranque sin USB · dual boot con Arch.

## Estructura del proyecto

```
hp-245-g8-jemg/
├── README.md                     ← Este archivo
├── macos/
│   ├── EFI/OC/                   ← EFI actual (generada)
│   ├── scripts/
│   │   ├── 05_generate_config.py ← Generador principal (con toggles)
│   │   └── 06_sync_usb_efi.sh    ← Sincronizacion a USB
│   ├── docs/
│   │   └── DIAGNOSTICO.md        ← Bitacora completa de biseccion
│   └── docs/otus9051-hp15s/      ← Referencia que SI arranca (mismo CPU)
└── .claude/                      ← Customizaciones de Ruflo / Claude Code
```

## Enlaces útiles indexados

- [Dortania AMD Zen Guide](https://dortania.github.io/OpenCore-Install-Guide/AMD/zen.html)
- [ChefKiss NootedRed](https://github.com/ChefKissInc/NootedRed)
- [ChefKiss Hackintosh Guide](https://chefkiss.dev/guides/hackintosh/)
- [VoodooPS2Controller (acidanthera)](https://github.com/acidanthera/VoodooPS2)

---

## Sync Script (06_sync_usb_efi.sh)

El script de sincronizacion ha sido mejorado significativamente:

- Prefiere montar sin sudo usando `udisksctl` cuando es posible.
- Ejecuta `rsync` sin sudo cuando el punto de montaje es escribible por el usuario.
- Por defecto hace **sync completo** (incluye todos los recursos, audios incluidos). Esto es mas seguro porque OpenCore podria notar archivos faltantes aunque `AudioSupport=false`.
- Para sync rapido durante muchas iteraciones de prueba:

  ```bash
  SYNC_FAST=1 ./scripts/06_sync_usb_efi.sh
  ```

  Esto excluye `OC/Resources/Audio/` (los ~360 archivos .mp3 del tema grafico).

El script tambien muestra el perfil actual del generador al terminar (si tienes `-NRedDPDelay` y si estas en modo ACPI minimal).

## Flujo de trabajo recomendado

```bash
cd macos

# 1. Editar el generador (fuente de verdad) si hace falta
nano scripts/05_generate_config.py

# 2. Regenerar el perfil deseado + validar
python3 scripts/05_generate_config.py --profile postinstall
./tools/ocvalidate ./EFI/OC/config.plist

# 3a. Sincronizar al USB (perfil install)
./scripts/06_sync_usb_efi.sh            # SYNC_FAST=1 para iterar sin los ~360 mp3 de audio

# 3b. O copiar al disco interno (perfil postinstall): MountEFI en macOS → reemplazar
#     EFI/OC/config.plist en el ESP del disco → Reset NVRAM (CleanNvram) → reiniciar.
```

## Reinstalar desde cero (referencia rápida)

1. Reconstruir el USB: `sudo ./scripts/07_rebuild_usb.sh /dev/sdX` (perfil install). Arrancar en puerto USB 2.0.
2. Recovery → Utilidad de Discos → **Erase** del disco destino (HDD WD, **nunca el NVMe**) en APFS/GUID.
3. Instalar. Si la fase de copia se congela, añadir `-NRedNoAccel` *manual en el picker* (solo esa sesión).
   **No** forzar apagados (corrompe el instalador staged → `LoadImage Unsupported`).
4. Tras instalar: copiar el EFI al disco interno con **MountEFI** (perfil postinstall). Ver `macos/docs/DIAGNOSTICO.md`.

**Última actualización**: 2026-06-02 — macOS Ventura **funcional** (iGPU/brillo/audio/batería/input OK),
arranca sin USB. Sistema de 3 perfiles de EFI. Pendiente: USB mapping real.
