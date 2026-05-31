# Diagnóstico Hackintosh — HP 245 G8 (Ryzen 3 5300U / Lucienne) — macOS Ventura

Bitácora del proceso de arranque del instalador de macOS Ventura 13 en un
HP 245 G8 con AMD Ryzen 3 5300U (Renoir/Lucienne, iGPU Vega `1002:164C`),
OpenCore 1.0.7 + NootedRed. Cada entrada = una causa raíz hallada y corregida.

## Hardware (Report.json de Hardware-Sniffer)
- **Placa:** HP 245 G8, BIOS **F.30**, UEFI, Secure Boot OFF, **Above 4G Decoding NO disponible**.
- **CPU:** Ryzen 3 5300U (Lucienne, family 17h, **4C/8T**).
- **iGPU:** Lucienne `1002:164C`, eDP 1366x768, VRAM 512 MB, Resizable BAR OFF. Path `\_SB.PCI0.GP17.VGA_`.
- **Audio:** Realtek ALC236 (`10EC:0236`), layout a determinar.
- **WiFi:** Realtek **RTL8822CE** (`10EC:C822`) — **sin driver macOS** (usar adaptador USB‑Ethernet RTL8153 para red).
- **NVMe:** Kingston NV3 (`2646:5028`). **SATA:** HDD WDC.
- **EC real:** `\_SB.PCI0.SBRG.EC0_` (cuelga de **SBRG**, no LPCB).

## Método
1. **Logs de OpenCore** (`opencore-*.txt` en la ESP, con `Misc>Debug>Target=67`): registran la fase **boot.efi** hasta `EXITBS:START`. NO capturan el kernel.
2. **Fotos de pantalla**: única fuente del verbose del **kernel** (tras ExitBootServices).
3. **EFI de referencia del mismo modelo** (`docs/hp-245-g8-efi-base/`, HP 245 G8 Ryzen 5 5500U) — patrón maestro que SÍ arranca.
4. **OpCore-Simplify** (`docs/OpCore-Simplify/`) — lógica algorítmica (config_prodigy/acpi_guru) y base de datos de hardware.
5. **Report.json** (Hardware-Sniffer) — perfil exacto con paths ACPI/PCI.

## Cronología de causas raíz (commits en `main`, local, sin trailers)

| # | Commit | Síntoma | Causa raíz | Fix |
|---|--------|---------|-----------|-----|
| 1 | `496f625` | instalador rebota al picker | falta driver HFS+ (BaseSystem.dmg es HFS+) | HfsPlus.efi + ConnectDrivers=True |
| 2 | `ab12b80` | cuelgue tras ExitBootServices, sin verbose | esquema de memoria "moderno" incompatible | Booter>Quirks **legacy** (EnableWriteUnprotector=True; Rebuild/SetupVirtual/SyncRuntime=False) |
| 3 | `b994608` | (git) ruido de tooling | node_modules/db/.swarm en el árbol | `.gitignore` ampliado |
| 4 | `4132ce0` | versión difícil / sin imagen | board-id daba Sequoia; Renoir sin framebuffer básico | objetivo **Ventura 13** + NootedRed ON |
| 5 | `b3d1c81` | negro + reinicio (panic FB) | SMBIOS MacBookPro16,3 no recomendado | SMBIOS **MacBookPro16,2** + `-NRedDPDelay` |
| 6 | `e8de66c` | **negro + reinicio sin verbose** | `Cpuid1Data` spoof Intel sobre parches AMD_Vanilla | **Cpuid1Data/Mask vacíos** + LapicKernelPanic=True |
| 7 | `67d906d` | (avance) kernel arranca, cuelga tardío | kexts incorrectos para HP/Ryzen | AmdTscSync→**ForgedInvariant**; quitar SMCDellSensors/SMCProcessor |
| 8 | `4d0f3ff` | **congela en enumeración PCI** (`pci ... flags 0xc000`) | **arrancaba con CERO ACPI** (único SSDT deshabilitado y con path LPCB inexistente) | **9 SSDTs reales** + parche **GPRW→XPRW** + quirks UEFI HP |

### Progreso de arranque observado
- Commits 1-5: no pasaba de ExitBootServices.
- Commit 6 (Cpuid1Data): **desbloqueo grande** — el kernel arranca y muestra verbose (`Darwin 22.5.0`).
- Commit 7-8: avanza hasta cargar todos los kexts y enumerar ACPI; se quedaba en la **fase PCI** por falta de SSDTs.

## Estado actual (tras commit `4d0f3ff`)
- **ACPI:** 9 SSDTs activos (EC, GPRW, USBX, PLUG-ALT, XOSI, PNLF, ALS0, PMC, HPET) + parche GPRW→XPRW. Validados con `iasl`.
- **Kexts (16):** Lilu, VirtualSMC, ForgedInvariant, SMCBatteryManager/SuperIO/LightSensor, NootedRed (ON), AppleALC/ALCU, USBToolBox/UTBDefault, VoodooPS2, NVMeFix, BrightnessKeys, RestrictEvents, AppleMCEReporterDisabler.
- **Booter>Quirks:** esquema legacy (EnableWriteUnprotector=True; Rebuild/SetupVirtual/SyncRuntime/DevirtualiseMmio=False; ResizeAppleGpuBars=-1).
- **Kernel:** Cpuid1Data vacío; DummyPowerManagement=True; LapicKernelPanic=True; ProvideCurrentCpuInfo=True; core-count=4 en parches AMD_Vanilla; `_mtrr` algrey ON (pendiente evaluar algrey OFF/shaneee ON).
- **UEFI>Quirks:** EnableVectorAcceleration=True, IgnoreInvalidFlexRatio=False, DisableSecurityPolicy=False, UnblockFsConnect=True.
- **SMBIOS:** MacBookPro16,2. **boot-args:** `-v keepsyms=1 debug=0x100 npci=0x3000 revblock=media revpatch=cpuname,memtab,sbvmm alcid=1 -NRedDPDelay`.
- **macOS:** Ventura 13 (board-id `Mac-4B682C642B45593E`).

## Pendiente
- **Validar con la DSDT real** (root-only; el usuario debe extraerla) que el parche GPRW→XPRW matchea y los paths de los SSDTs existen.
- **USB mapping** (USBToolBox/USBMap) — requiere la DSDT y mapear puertos en macOS.
- Tras arrancar: evaluar `_mtrr` algrey OFF/shaneee ON (OpCore-Simplify lo recomienda para iGPU AMD), layout de audio ALC236.

## Decisiones de juicio (fuentes en conflicto)
- **Booter>Quirks:** OpCore-Simplify (heurística) sugiere esquema moderno; el **EFI de referencia (empírico, mismo modelo)** usa legacy. Gana la evidencia: legacy (ya se pasa ExitBootServices con él).
- **DummyPowerManagement=True:** la referencia usa False porque añade AMDRyzenCPUPowerManagement.kext; nosotros no lo tenemos, así que True (estándar AMD).

## Sesión 2026-05-30 (cont.) — los SSDTs no bastaron; bisección
- Con los 9 SSDTs el ACPI carga (foto confirma OCLT CpuPlug, SsdtUsbx, GPRW, XOSI
  en la lista ACPI) pero el kernel **sigue congelado en el mismo punto exacto**:
  `pci (build 22:12:01 Jun 8 2023), flags 0xc000` + `Couldn't alloc class
  "AppleKeyStoreTest"` (este último benigno). → **ACPI descartado** como causa del freeze.
- El freeze real está tras la enumeración PCI = transición gráfica/almacenamiento.
- **Bisección paso 1 (commit `8d99e9f`):** `-NRedNoAccel` (NootedRed framebuffer-only,
  sin aceleración Metal). Ataca la causa #1 en Renoir con VRAM 512 MB. Reversible.
- Próximos pasos si no avanza: NootedRed OFF (aísla gráficos) → si sigue colgado es
  USB mapping (UTBDefault genérico) / NVMe Kingston NV3 / probar `npci=0x2000`.
- Errores ACPI en la foto (`AE_ALREADY_EXISTS` _Q50/_CRS, "3 table load failures,
  28 successful"): benignos; SSDT-HPET no carga sin su parche `_CRS→XCRS` (no crítico).

## Sesión 2026-05-30 (cont. 2) — workflow de recuento + alinear parches PCI
- Workflow de 5 agentes (auditoría repo + 2 investigaciones web + comparación REF + síntesis).
- Hallazgo: el cuelgue en `pci flags 0xc000` se ataca alineando los parches Kernel con
  la EFI de referencia (azurejelly, mismo modelo, que arranca), NO tocando MMIO.
- Cambios (commits `99255a5`, `1d38278`, `6f8a3c2`):
  - `IOPCIIsHotplugPort` (AM5, escritorio) -> OFF (igual que la ref).
  - `probeBusGated` -> ON (la ref lo tiene ON).
  - `_mtrr_update_action`: de 4 ON a EXACTO de la ref -> shaneee(17-23)=ON,
    algrey(17-23)=OFF, algrey(24+)=ON, shaneee(24+)=OFF. Elimina el doble parche
    sobre el mismo patrón PAT/MTRR (conflicto, posible causa del cuelgue temprano).
  - npci de vuelta a 0x3000 (las 3 EFIs que arrancan lo usan).
- ResizeAppleGpuBars=-1, ResizeGpuBars=-1, DeviceProperties iGPU vacío: ya correctos.
- Kernel>Patch ahora IDÉNTICO a la referencia. Pendiente probar arranque.
- Si AÚN cuelga en PCI: `nvme=-1` (descartar Kingston NV3 DRAM-less) + USB en puerto 2.0.

## Sesión 2026-05-30 (cont. 3) — atacar USB (elección del usuario)
- Tras alinear Kernel>Patch con la ref, sigue colgando en `pci flags 0xc000` (foto img3,
  cargan menos ACPI por los parches alineados pero el freeze es el mismo).
- Usuario eligió: atacar el USB.
- **SSDT-USB-Reset (commit `91938fb`):** desactiva RHUB de XHC0/XHC1 bajo Darwin para
  re-enumerar USB. Validado vs DSDT real: \_SB.PCI0.GP17.XHC0/XHC1, RHUB sin _STA propio
  (sin parche XSTA). 12 puertos totales (<15, sin XhciPortLimit). Plantilla = OpCore-Simplify.
- **Prueba física pendiente del usuario:** arrancar el pendrive instalador en un puerto
  USB 2.0 (no 3.0/azul) — reduce la complejidad de enumeración USB en esta fase.
- Si AÚN cuelga: queda el NVMe Kingston NV3 DRAM-less (probar SSDT que lo deshabilite o
  `nvme=-1`), o clonar la EFI de azurejelly tal cual.

## Sesión 2026-05-30 (cont. 4) — GIRO: el cuelgue NO es PCI, es el FRAMEBUFFER
- Workflow de investigación profunda (8 agentes, 610k tokens). Hallazgo decisivo:
  **`pci (build...) flags 0xc000` es un banner INFORMATIVO de IOPCIFamily, NO un
  error**. La enumeración PCI YA pasó. El verbose se corta ahí porque lo siguiente
  es la inicialización del framebuffer del iGPU Lucienne (toma el panel eDP, el
  mismo canal del verbose). Fuente: apple-oss IOPCIFamily/IOPCIConfigurator.cpp.
  -> Veníamos atacando la fase equivocada (npci, SSDTs bridge, parches PCI).
- `Couldn't alloc class AppleKeyStoreTest` = línea benigna, no el cuelgue.
- **Causa real más probable:** framebuffer del iGPU Lucienne (NootedRed/eDP).
  Pista clave: el 5500U (Vega 7, **1GB VRAM**) arranca; el 5300U (Vega 6, **512MB
  VRAM**) no -> sospechoso #1 = VRAM <1GB (umbral NootedRed).
- `nvme=-1` retirado (commit `1cbf8af`): prueba inválida. NVMeFix ya presente.
- NO volver a tocar: npci, parches PCI, SSDTs de bridge, Cpuid1Data, core-count.

### PLAN (post-giro), por confianza×facilidad:
1. [USUARIO, decisivo, gratis] Arrancar y conectar **monitor HDMI externo** + hacer
   **ping** al equipo desde otro dispositivo. Distingue "negro pero vivo"
   (=framebuffer/eDP) de "cuelgue real de I/O". Si el HDMI muestra el instalador ->
   instalar por HDMI.
2. [YO] Aislar GPU: NootedRed.kext **Enabled=False** + `-radvesa` (distinto de
   -NRedNoAccel, que sigue cargando el kext). Si arranca en VESA -> es NootedRed.
3. [USUARIO] Subir UMA/VRAM a >=1GB con **Smokeless-UMAF** (BIOS HP lo oculta).
4. [YO] SMBIOS MacBookPro16,3 (el de la ref que arranca).
5. [USUARIO] Si 1-4 fallan: instalar **Sonoma 14** (no Monterey), versión de la ref.
- Veredicto del workflow: alcanzable; última milla = framebuffer; único límite duro
  plausible = VRAM 512MB. NO es el NVMe (no comprar disco aún).

## Sesión 2026-05-30 (cont. 5) — VRAM subida a 2 GB (BIOS)
- El usuario subió el UMA Frame Buffer a **2 GB** desde la BIOS HP F.30 (la opción
  SÍ existía). Confirmado en Linux: radeontop 2019M VRAM, glxinfo 2048MB, vulkaninfo
  heap 2.91 GiB. Antes 512 MB (por debajo del umbral ~1GB de NootedRed = sospechoso #1).
- **NO requiere config nueva en el EFI:** NootedRed lee la VRAM del firmware; no se
  fija por config.plist. DeviceProperties de la iGPU debe seguir VACÍO (correcto).
- Pendiente: arrancar y ver si ahora pasa el framebuffer (la hipótesis VRAM se prueba
  solo arrancando; nada que editar).

## Sesión 2026-05-31 — receta Otus9051 (EFI del 5300U EXACTO que arranca)
- VRAM a 2GB NO resolvió el cuelgue del framebuffer -> descartada como causa única.
- Hallazgo del usuario (vía Grok): repo Otus9051/Hackintosh-HP-15s-eq2144au, EFI que
  arranca Ventura en Ryzen 3 5300U EXACTO (Vega 6). Clonado en docs/otus9051-hp15s.
- Su receta de gráficos CONFIRMA la nuestra: NootedRed sin DeviceProperties iGPU.
  Pero difiere en 5 cosas -> aplicadas a nuestro EFI (commit `1c8f1f9`):
  1. SMBIOS iMac20,1 (no MacBookPro16,2). board-id Mac-CFF7D910A743CAAF.
  2. +AMDRyzenCPUPowerManagement +SMCAMDProcessor (v1.6.0) y DummyPowerManagement=False.
  3. DisableIoMapper=True. 4. ReleaseUsbOwnership=True.
  5. boot-args limpios: "-v keepsyms=1 debug=0x100 npci=0x3000 alcid=13".
- NootedRed se queda en 0.8.10 (el "1.0.0" del Otus es build viejo; 0.8.10 es el
  release oficial más nuevo). DeviceProperties iGPU vacío (igual que Otus).
- Diferencias de hardware Otus(HP 15s) vs nuestro(245 G8): su ACPI es de su chasis;
  nosotros mantenemos NUESTROS 10 SSDTs (validados vs DSDT real). 
- Pendiente: arrancar. Si funciona -> era SMBIOS/power management. Si no -> evaluar
  probar el EFI Otus casi tal cual, o cambiar a Sonoma.

## Sesión 2026-05-31 (cont. 6) — alineación del generador + verificación post-Otus
- `python3 -m py_compile scripts/05_generate_config.py` → **COMPILA OK** (sin errores de sintaxis tras los edits de quirks/kexts/SMBIOS).
- Ejecutado `python3 scripts/05_generate_config.py`:
  - SMBIOS: iMac20,1 | 18 kexts | 25 patches AMD_Vanilla (cores=4)
  - DisableIoMapper=True, DummyPowerManagement=False, ReleaseUsbOwnership=True
  - boot-args: -v keepsyms=1 debug=0x100 npci=0x3000 alcid=13
  - Power kexts (AMDRyzenCPUPowerManagement + SMCAMDProcessor) presentes con binarios
  - ocvalidate local: "No issues found"
- Script 06_sync_usb_efi.sh mejorado: rsync completo de EFI/OC (--delete), defaults a /run/media/$USER/MACOS, validación ocvalidate post-sync.
- Estado del generador: 100% alineado con la receta del Otus9051 (5300U que arranca). UUID/ROM se regeneran en cada run (diseño intencional).
- Pendiente inmediato del usuario: insertar USB → correr `./scripts/06_sync_usb_efi.sh` (o con MOUNT_POINT explícito) → arrancar en puerto USB 2.0.
- Próxima prueba: con la receta Otus completa (power AMD real + iMac20,1 + DisableIoMapper). Si aún cuelga en framebuffer → siguiente bisección es NootedRed nightly más reciente o ACPI minimal del Otus (PLUG-ALT + rmne + RTCAWAC).

## Sesión 2026-05-31 (cont. 7) — RESUELTO: "OC: failed to load configuration" (BOOTx64.efi mal)
- **Síntoma:** tras un `mkfs.vfat` fresco del USB, OpenCore arrancaba pero abortaba con
  `OC: Failed to load configuration!` en bucle. El config era válido (ocvalidate 1.0.7 OK,
  byte-idéntico USB/local), todos los kexts/SSDTs/drivers presentes, versiones 1.0.7
  consistentes. No era el config.
- **Causa raíz (confirmada en la fuente de OpenCore):** `EFI/BOOT/BOOTx64.efi` era una
  **copia íntegra de `OpenCore.efi`** (626688 B, md5 `c171f38a`) en vez del **Bootstrap**
  (24576 B, md5 `c2e80064` en 1.0.7). En `Application/OpenCore/OpenCore.c` (`OcBootstrap`),
  OpenCore deriva su raíz del **directorio del .efi en ejecución** y lee `config.plist`
  ahí. Arrancando desde `\EFI\BOOT\` buscaba `\EFI\BOOT\config.plist` (inexistente) → muere.
  La redirección `EFI\BOOT\BOOTx64.efi → EFI\OC\OpenCore.efi` SOLO existe en el Bootstrap
  (`Application/Bootstrap/Bootstrap.c:91`), no en OpenCore.efi.
- **Por qué se destapó ahora:** el config tiene `Misc.Boot.LauncherOption=Full`, que
  auto-registra una entrada NVRAM a `\EFI\OC\OpenCore.efi`; mientras existía, arrancaba
  por NVRAM (saltándose el BOOTx64 malo). El `mkfs.vfat` invalidó esa entrada (cambió el
  GUID de partición) y el firmware HP cayó al fallback `\EFI\BOOT\BOOTx64.efi`. El binario
  malo estaba en git desde el commit inicial del EFI (`a4954c0`): nunca funcionó por
  fallback, solo por NVRAM.
- **Fix aplicado:** descargado el release oficial OpenCore 1.0.7; verificado que nuestro
  `OpenCore.efi` y `OpenRuntime.efi` son byte-idénticos al oficial (genuinos). Reemplazado
  `EFI/BOOT/BOOTx64.efi` por el Bootstrap real (24576 B) en local y USB. ocvalidate OK.
- **Veredicto scripts:** `06_sync_usb_efi.sh` NO hace mkfs (lo hace el usuario a mano) y
  sincroniza EFI/ completo con `rsync --delete`, así que propagará el Bootstrap correcto en
  cada sync. No fue culpable del binario malo; el detonante fue la práctica de `mkfs.vfat`.
- **Resultado:** OpenCore ahora carga y muestra el picker. ✅

## Sesión 2026-05-31 (cont. 8) — NUEVO MURO: "OCB: StartImage failed - Already Started"
- **Síntoma:** el picker carga, se selecciona "macOS"/instalador, imprime "OK" y salta
  `OCB: StartImage failed - Already Started`, se resetea y vuelve al picker en bucle.
- **Caracterización (Dortania + foro AMD-OSX):** `StartImage` devuelve `EFI_ALREADY_STARTED`.
  No es un problema del config.plist en sí; es **confusión de la entrada de arranque / NVRAM**
  (el firmware re-entra en OpenCore / handle de imagen ya iniciado). Dortania lo asocia a
  multiboot con Windows (no es nuestro caso, no hay Windows en el USB); el foro AMD-OSX lo
  resuelve con **reset de NVRAM + cold boot + fijar prioridad de arranque en BIOS**.
- **Hipótesis para nuestro caso:** encaja con el churn de NVRAM reciente — tras el `mkfs.vfat`
  y el fix del Bootstrap, hay probablemente una **entrada NVRAM "OpenCore" rancia** apuntando
  a una ruta/partición vieja, mientras `LauncherOption=Full` intenta re-registrar → re-entrada.
- **Plan (próxima sesión), por confianza×facilidad:**
  1. [USUARIO] **Reset NVRAM**: en el picker de OpenCore pulsar **espacio** → seleccionar
     `Reset NVRAM` (o `CleanNvram.efi`), luego **cold boot** (apagado total, no reset).
  2. [USUARIO] En BIOS HP F.30: limpiar entradas de arranque viejas y dejar el USB primero.
  3. [YO, si persiste] evaluar `Misc.Boot.LauncherOption=Disabled` para que OpenCore deje de
     re-registrarse en NVRAM (evita la entrada rancia que causa la re-entrada).
  4. Confirmado que NO es el framebuffer aún: ni siquiera llega a cargar el kernel; es la fase
     de StartImage del boot.efi del instalador. El muro del framebuffer (Vega 6) sigue
     pendiente más adelante.

## Sesión 2026-05-31 (cont. 9) — causa raíz "Already Started" confirmada con los .txt
- LauncherOption=Disabled NO bastó (el log `opencore-2026-05-31-060153.txt` post-cambio
  seguía en bucle). **Lección:** leer SIEMPRE los `opencore-*.txt` de la ESP antes de teorizar
  (lo había diagnosticado a ojo desde la pantalla).
- Los `.txt` revelan los prefijos reales y la secuencia:
  `OCM: Failed to start image` / `BS: Failed to start OpenCore image` /
  `BS: Failed to load OpenCore from disk` / `OC: Boot failed` / `OCB: StartImage failed`,
  todos `Already started`. Confirmado en fuente: `BS:` = Bootstrap
  (`Application/Bootstrap/Bootstrap.c:134,189`), `OCB:` = `BootEntryManagement.c:2593`.
- **Causa raíz:** que OpenCore ESCRIBA el `.txt` prueba que arranca y carga config OK. La
  entrada que se selecciona en el picker apunta al **propio launcher de OpenCore** (entrada
  de arranque NVRAM **autorreferencial**, residuo de cuando `LauncherOption=Full`). El
  Bootstrap se re-ejecuta e intenta arrancar `OpenCore.efi` ya iniciado → `EFI_ALREADY_STARTED`
  → bucle. `Disabled` evita crear entradas nuevas pero NO borra la rancia.
- **Fix aplicado:** `LauncherOption=Disabled` + herramienta **CleanNvram.efi** en `Misc.Tools`
  (Auxiliary=False = siempre visible; `FullNvramAccess=True` — el schema 1.0.7 lo EXIGE;
  binario del release oficial 1.0.7 en `EFI/OC/Tools/`). `AllowNvramReset` se descartó: no
  existe en el schema 1.0.7 (ocvalidate lo rechaza). ocvalidate OK, sincronizado al USB.
- **Próximo paso del usuario:** arrancar → en el picker elegir **"Reset NVRAM (CleanNvram)"**
  → cold boot. Resetear NVRAM es seguro (los boot-args se re-inyectan vía NVRAM>Add). Tras
  limpiar, seleccionar macOS debería arrancar el instalador de verdad → ahí reaparece el
  muro real del framebuffer (Vega 6).

## Sesión 2026-05-31 (cont. 10) — RESUELTO el bucle: faltaba el instalador + el Bootstrap no arranca en este firmware
- CleanNvram NO arregló el bucle (limpiar NVRAM no cambió nada) → la hipótesis "NVRAM rancia"
  de cont.9 era incorrecta/incompleta. Releyendo los `.txt` y la fuente, dos causas reales:
  1. **El USB NO tenía instalador de macOS.** El `mkfs.vfat` borró `com.apple.recovery.boot/`
     y solo se re-sincronizó el `EFI/`. Sin macOS que arrancar, la ÚNICA entrada del picker
     era OpenCore mismo → cualquier selección = "Already Started". (`ls` del USB: solo EFI,
     logs y tools; cero `BaseSystem.dmg`/recovery.)
  2. **El Bootstrap no puede arrancar OpenCore en este firmware HP.** El log muestra
     `OCM: Failed to start image - Already started` en el segundo 0, desde
     `OcLoadAndRunImage` (`Library/OcMiscLib/ImageRunner.c:110`, carga OpenCore.efi desde
     buffer). Firmware "frágil" (ref OpenCore bugtracker #712/#1502). Históricamente arrancaba
     por una entrada NVRAM DIRECTA a `\EFI\OC\OpenCore.efi`, que el `mkfs.vfat` invalidó.
- **Fix aplicado (ambas cosas):**
  1. Restaurado el instalador: copiado `recovery_ventura/com.apple.recovery.boot/` (Ventura 13,
     board `Mac-4B682C642B45593E`, BaseSystem.dmg 706568592 B) a la raíz del USB. (El otro
     cache `recovery/` 884 MB es Sequoia 15.x via `Mac-937A206F2EE63C01`; NO usar.)
  2. Arranque directo: creada entrada UEFI con
     `sudo efibootmgr -c -d /dev/sdb -p 1 -L OpenCore-HP245 -l '\EFI\OC\OpenCore.efi'`
     → `Boot0000* OpenCore-HP245  HD(1,GPT,4bae763e-…)/\EFI\OC\OpenCore.efi`, primera en
     BootOrder. Arranca OpenCore directo (sin el Bootstrap roto). Funciona en cualquier puerto
     (referencia por GUID GPT). Si se reformatea el USB, re-ejecutar efibootmgr.
- **RESULTADO — la cadena de arranque está RESUELTA.** El picker muestra "macOS external dmg"
  (entra) vs "no dmg" = OpenCore (Already Started, no elegir). Seleccionando el dmg, **el kernel
  de Ventura ARRANCA**: cargan los 21 SSDTs (3 fallos benignos `_Q50/_CRS/CpuPlug AE_*`),
  **NootedRed carga** (banner NRed), RestrictEvents 1.1.6, AppleCredentialManager. El log
  boot.efi llega a `EXITBS:START` (handoff limpio al kernel). El verbose en pantalla se corta
  en `pci (build 22:12:01 Jun 8 2023), flags 0xc0080` → **el muro del framebuffer Vega 6**
  (el panel eDP toma el canal del verbose). `Couldn't alloc AppleKeyStoreTest` = benigno.
- Anotado: `OC: Kernel patcher result 22 (Shaneee | _mtrr_update_action | Fix PAT) - Not Found`
  — un parche `_mtrr` no matchea en el kernel de Ventura (revisar si el muro del FB persiste).
- **Próximo paso (decisivo, del usuario, sin hardware extra):**
  1. **HDMI externo** (conectado antes de encender): ¿muestra el instalador aunque la interna
     esté negra? SÍ → problema solo del panel eDP → instalar por HDMI.
  2. **LED de Bloq Mayús** con la pantalla congelada: si responde → kernel vivo (solo display).
  - Si "vivo pero negro": aislar NootedRed (OFF + `-radvesa` = VESA) o ajustes eDP de NootedRed.

