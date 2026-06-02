# Guía — USB mapping real (HP 245 G8, Ryzen 3 5300U)

Reemplaza el placeholder `UTBDefault.kext` por un mapa de puertos USB **real** generado en
macOS con **USBMap (corpnewt)**. Se integra en el perfil `postinstall` del generador.

> **No es urgente:** el sistema ya funciona con `UTBDefault`. Hazlo cuando tengas un rato y dos
> pendrives a mano. El mapa real activa bien todos los puertos (incl. webcam/BT internos) y evita
> que macOS desactive puertos al azar por el límite de 15 puertos por controlador.

## Contexto del hardware

- macOS solo admite **15 puertos USB por controlador**.
- El Renoir/Lucienne tiene **2 controladores** (XHC0 y XHC1, ~6 puertos cada uno) → estás lejos
  del límite, el mapeo es sencillo y `XhciPortLimit` puede quedarse en `False`.

## Preparación

1. Un dispositivo **USB 2.0** y uno **USB 3.0** distintos (para identificar cada puerto).
2. Trabajas **desde macOS Ventura** (ya instalado). No hace falta Windows.

## Pasos en macOS

**1. Descargar USBMap:**
```bash
git clone https://github.com/corpnewt/USBMap
cd USBMap
```

**2. Lanzarlo** (pide contraseña; monta kexts temporales):
```bash
./USBMap.command
```

**3. Discover Ports (opción `D`).** Mapeo físico. Para **cada puerto USB-A físico**, uno por uno:
- Inserta el **USB 2.0** → espera a que aparezca una personalidad nueva (`HSxx`) → Enter.
- Saca el USB2, inserta el **USB 3.0** en el **mismo** puerto → detecta `SSxx` → Enter.
- Repite en el siguiente puerto físico.
- **Puerto USB-C:** pruébalo en **ambas orientaciones** (dale la vuelta al conector).
- Los **internos** (webcam, Bluetooth, lector SD si lo hay) aparecen solos sin enchufar nada — anótalos.

**4. Select Ports.** Marca solo puertos reales + internos. Asigna el **tipo** (connector) a cada uno:

| Puerto | Tipo |
|---|---|
| USB-A (USB 2.0) | `0` |
| USB-A (USB 3.0) | `3` |
| USB-C | `9` (Type-C con switch) |
| Webcam / Bluetooth / SD internos | `255` (interno) |

> Mantén cada `SSxx` (USB3) junto a su `HSxx` (USB2) compañero del mismo puerto físico.

**5. Build USBMap.kext (opción `B`).** Cuando pregunte el SMBIOS, pon **`iMac20,1`**.
Genera `USBMap.kext` (codeless, ligado al SMBIOS).

## Integración en el repo

Trae el `USBMap.kext` al equipo del repo (o pásalo) y luego:

1. Copiar a `macos/EFI/OC/Kexts/USBMap.kext`.
2. Ajustar `scripts/05_generate_config.py` — perfil `postinstall`:
   - Quitar `UTBDefault` **y** `USBToolBox` (USBMap es codeless, no necesita el kext de USBToolBox).
   - Añadir `USBMap` a `extra_kexts`.
   > Alternativa: si en vez de corpnewt usas la *tool* de USBToolBox en modo **companion**, genera
   > `UTBMap.kext` (que SÍ depende de `USBToolBox.kext`); en ese caso se mantiene `USBToolBox` y se
   > añade `UTBMap` (el generador ya contempla este caso en el bloque `usb="utbmap"`).
3. Regenerar: `python3 scripts/05_generate_config.py --profile postinstall`
4. Validar: `./tools/ocvalidate ./EFI/OC/config.plist`
5. Copiar el `config.plist` al ESP del disco interno con **MountEFI** → Reset NVRAM → reiniciar.

## Verificación (tras aplicarlo)

```bash
ioreg -p IOUSB -l -w 0 | grep -i "port"
```
Cada puerto debería mostrar sus dispositivos sin que ninguno "desaparezca".

## Atajo de validación

El EFI de referencia del **mismo modelo** (`docs/hp-245-g8-efi-base/Kexts/USBMap.kext`) ya define
XHC0 (`pcidebug 4:0:3`) y XHC1 (`4:0:4`), 6 puertos cada uno. Sirve para **comparar** que tu
resultado tiene sentido — pero genera el tuyo (los puertos físicos exactos dependen de tu unidad).
Si lo adoptaras directo, cambia su `model` de `MacBookPro16,3` a `iMac20,1`.
