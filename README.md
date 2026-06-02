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

## Estado actual — macOS Ventura INSTALADO y arrancando sin USB (2026-06-02)

**HITO ALCANZADO**: macOS Ventura 13 instalado en el HDD interno (`sda2`, APFS) y arrancando
desde el EFI del disco interno (`sda1`) **sin la USB**. Dual boot con Arch Linux (NVMe) intacto.

- Secuencia confirmada: instalador → copia/extracción → reinicios → primer boot desde disco → escritorio.
- **Teclado interno y touchpad funcionan** (fix de sub-plugins PS2/I2C + parche `_OSI→XOSI`).
- **NootedRed activo** — pendiente verificar aceleración iGPU completa (Metal/VRAM) en post-install.
- Lo que faltó durante la instalación: añadir `-NRedNoAccel` manualmente en el picker (solo para
  esa sesión, no va en el config) para pasar el muro del framebuffer en la fase de copia.
- Lo que destrabó la instalación: **USB reconstruido limpio** (sin firma iso9660 residual) +
  quirks alineados con Otus9051 + `agdpmod=pikera`. Ver `macos/docs/DIAGNOSTICO.md`.
- Generador (`05_generate_config.py`) es la fuente de verdad del `config.plist`.

### Config que funciona (estado actual del EFI)

| Parametro | Valor |
|---|---|
| macOS | Ventura 13 — instalado en `sda2` (APFS) |
| NootedRed | v0.8.10 — HABILITADO |
| AMDRyzenCPUPowerManagement | DESHABILITADO (causa kernel panic) |
| SMCAMDProcessor | DESHABILITADO (depende del anterior) |
| DummyPowerManagement | True |
| TSC sync | ForgedInvariant v1.5.0 |
| SSDT CPU | SSDT-PLUG-ALT.aml (version AMD) |
| Booter/Kernel quirks | `DevirtualiseMmio`/`ProtectUefiServices`/`DisableIoMapper`/`LapicKernelPanic` = False (alineado Otus9051) |
| boot-args | `-v keepsyms=1 debug=0x100 npci=0x3000 alcid=13 agdpmod=pikera -NRedDPDelay` |
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
| VoodooPS2Controller | ON | Teclado/trackpad (no funciona en Recovery aun) |
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

## Tests pendientes (instalador ya arranca — ahora a instalar)

El instalador de Recovery arranca correctamente. Los tests de framebuffer anteriores quedan superados. Lo que queda:

### Prioridad alta (instalacion + teclado/touchpad)

1. **Instalar macOS Ventura** usando mouse USB externo para navegar el Recovery (el teclado interno no funciona, pero el mouse USB si).
2. **Reparar teclado interno y touchpad** — VoodooPS2Controller esta cargado pero no enumerando el dispositivo PS2. Ver seccion "Siguiente paso".
3. **USB mapping real** — UTBDefault es un placeholder; hacer el mapping correcto para este HP con USBToolBox desde macOS.
4. **AMD CPU Power Management** — una vez instalado, probar reactivar AMDRyzenCPUPowerManagement + SMCAMDProcessor (desactivar DummyPowerManagement).

### Prioridad media (post-instalacion)

5. **Audio** — AppleALC + alcid=13 ya configurado, verificar que funciona tras instalar.
6. **Brillo de pantalla** — SSDT-PNLF incluido, verificar control de brillo con BrightnessKeys.
7. **Bateria** — SMCBatteryManager incluido, verificar lecturas correctas.
8. **WiFi** — RTL8822CE no tiene soporte nativo; usar dongle USB-Ethernet para conectividad.

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

## Estado actual de pruebas (2026-05-31)

**HITO CONFIRMADO**: El instalador de macOS Ventura arranca exitosamente en el HP 245 G8.

- Secuencia de arranque: lineas blancas (verbose) → logo Apple → pantalla Recovery de macOS Ventura.
- Pantalla interna funciona con NootedRed v0.8.10 habilitado.
- **Teclado interno y touchpad PS2 no funcionan** en el Recovery. VoodooPS2Controller esta cargado pero no detecta el dispositivo PS2 de este HP.
- **Mouse USB externo funciona** correctamente — workaround disponible para navegar el instalador.
- El proximo paso es proceder con la instalacion y luego reparar los dispositivos de entrada.

## Flujo de trabajo recomendado

```bash
# 1. Editar toggles en el generador
nano scripts/05_generate_config.py

# 2. Regenerar + validar
python3 scripts/05_generate_config.py
./tools/ocvalidate ./EFI/OC/config.plist

# 3. Sincronizar (completo por defecto)
./scripts/06_sync_usb_efi.sh

# O version rapida (sin audios)
SYNC_FAST=1 ./scripts/06_sync_usb_efi.sh
```

## Siguiente paso

El Recovery arranca. Estos son los pasos concretos para continuar:

### 1. Instalar macOS Ventura

- Conectar mouse USB externo (el teclado interno no funciona aun en Recovery).
- Arrancar desde el USB con el pendrive en puerto USB 2.0 (negro).
- En el Recovery: Utilidades de Disco → formatear el NVMe como APFS, GPT.
- Lanzar "Reinstalar macOS Ventura" → seleccionar el NVMe formateado.
- La instalacion requiere internet. Usar dongle USB-Ethernet (RTL8153) conectado al hub o directo.
- El proceso tarda ~30 minutos. El equipo reinicia varias veces; en cada reinicio seleccionar la entrada del NVMe (no el USB) en el picker de OpenCore.

### 2. Post-instalacion: reparar teclado interno y touchpad PS2

El problema probable es que VoodooPS2Controller no esta enumerando el PS2 de este HP. Pasos para diagnosticar y reparar:

1. **Verificar que el PS2 aparece en ACPI**: buscar `PS2K` o `PS2M` en `macos/docs/DSDT.dsl`. Si no hay dispositivo PS2 declarado en la DSDT, hay que crear un SSDT que lo declare.
2. **Revisar logs de arranque** (opencore-*.txt en la ESP) buscando errores de VoodooPS2.
3. **Probar VoodooPS2Controller nightly** de ChefKiss si el de acidanthera no funciona con este HP.
4. **SSDT-PS2**: algunos HP con BIOS AMI necesitan un SSDT que declare el dispositivo PS2 explicitamente (`_SB.PCI0.LPC0.PS2K`). El path exacto se saca de la DSDT volteada de este equipo.
5. **Alternativa temporal**: usar un teclado USB externo + mouse USB para la post-instalacion mientras se resuelve el PS2.

### 3. Completar la post-instalacion

Una vez que el sistema arranque desde el NVMe:

- **USB mapping real**: ejecutar USBToolBox desde macOS, generar un `UTBMap.kext` especifico para este HP (reemplaza el UTBDefault generico).
- **AMD CPU PM**: probar habilitar AMDRyzenCPUPowerManagement + SMCAMDProcessor, deshabilitar DummyPowerManagement.
- **Verificar audio**: AppleALC con alcid=13 deberia funcionar; si no, probar alcid=11 o alcid=99.
- **Verificar brillo**: BrightnessKeys + SSDT-PNLF. Si no funciona revisar el path del panel en SSDT-PNLF contra la DSDT.
- **Montar EFI del NVMe**: una vez que todo funcione, copiar el EFI al NVMe para arrancar sin USB.

**Ultima actualizacion**: 2026-05-31 — Recovery de macOS Ventura arranca exitosamente. Pendiente: instalacion + teclado/touchpad PS2.
