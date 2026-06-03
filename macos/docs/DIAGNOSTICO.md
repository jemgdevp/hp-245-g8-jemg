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

## Sesión 2026-05-31 (cont. 11) — Diagnóstico: eDP link-training + Booter Quirks modernos

### Síntoma confirmado
- LED Bloq Mayús **no responde**. Logs blancos idénticos a imagen anterior: se corta en
  `pci (build 22:12:01 Jun 8 2023), flags 0xc080`.
- **Diagnóstico de consenso (usuario + Grok + issue #206 NootedRed):** el sistema
  **está vivo**. El Bloq Mayús no responde en ese punto porque el controlador PS/2
  (VoodooPS2) aún no terminó de inicializar su capa HID — NO significa CPU congelado.
  El verbose se corta porque **NootedRed toma el canal eDP del panel interno** para
  inicializar el framebuffer; desde ese momento el verbose ya no llega a la pantalla.
- **Issue #52 (NootedRed):** `link training FAIL` del panel eDP es muy común en laptops
  HP Ryzen 5000U (Lucienne). **Issue #206 (NootedRed):** en estos equipos el HDMI externo
  funciona aunque la interna quede negra.

### Por qué HDMI es la prueba decisiva
- Otus9051 (Ryzen 3 5300U exacto): lista "External Display via HDMI" como funcional en Ventura.
- azurejelly (HP 245 G8, mismo modelo): pantalla interna negra + HDMI full con aceleración.
- Si HDMI muestra el instalador → instalar por HDMI; la pantalla interna se afina después.

### Parche `_mtrr_update_action` "Not Found" — CERRADO como benigno
- Log cont.10: `OC: Kernel patcher result 22 (Shaneee | _mtrr_update_action | Fix PAT) - Not Found`.
- AMD_Vanilla incluye DOS entradas para el PAT fix: Shaneee y Algrey. Ambas abordan el
  mismo patrón pero con firma distinta según versión de kernel. Si Shaneee no matchea el
  kernel exacto de Ventura pero Algrey sí, **el PAT fix SE APLICA igualmente vía Algrey**.
- El generador activa TODOS los patches de AMD_Vanilla (Enabled=True). El "Not Found" de
  Shaneee es un warning de patcher normal; no es el cuelgue. **No requiere acción.**

### Cambios aplicados (commit `sesión-11`)
1. **Booter Quirks → esquema MODERNO** (el que usa Otus9051, el 5300U que arranca Ventura):
   - `RebuildAppleMemoryMap=True`, `SetupVirtualMap=True`, `SyncRuntimePermissions=True`
   - `EnableWriteUnprotector=False`, `DevirtualiseMmio=True`, `ProtectUefiServices=True`
   - Anterior (legacy): funcionaba para pasar ExitBootServices (sesión 2) pero impedía
     el correcto mapeo MMIO del framebuffer Lucienne según AMD-OSX.
   - Si cuelga tras ExitBootServices → revertir a legacy.
2. **Toggle `USE_NRED_NO_ACCEL`** en el generador (default=False): activa `-NRedNoAccel`
   que fuerza NootedRed a modo framebuffer-only sin Metal. Útil si el cuelgue está
   en la inicialización de la aceleración, no en el panel.

### Plan de arranque (sesión 11)
1. **[USUARIO — PRIMERO]** Conectar HDMI **antes** de encender. Si el instalador aparece
   por HDMI → el sistema vive, el problema es solo el panel eDP. Instalar por HDMI.
2. **[USUARIO — si no]** Anotar si el verbose avanza más con los quirks modernos o se
   detiene antes (ExitBootServices = retroceso → revertir a legacy).
3. **[YO — si el muro persiste]** Activar `USE_NRED_NO_ACCEL=True` + probar HDMI;
   si arranca sin aceleración → el fallo está en Metal/compute, no en el panel.
4. **[Fallback]** `AMDRyzenCPUPowerManagement` + `SMCAMDProcessor` — si el Bloq Mayús
   realmente no responde *después de esperar >2 min* → sí podría ser un panic real de
   estos kexts (el README de ryzen-hackintosh los marca como optativos y riesgosos).
   Se desactivan + `DummyPowerManagement=True` y se reprueba.

---

## Sesión 2026-05-31 (cierre) — Notas de cierre, deudas técnicas y referencias nuevas

### Referencia nueva: azurejelly (HP 245 G8, Ryzen 5 5500U, mismo chasis)
- EFI confirmado que arranca Ventura con pantalla interna negra + HDMI full con aceleración.
  Mismo patrón esperado para nuestro 5300U.
- SMBIOS: `MacBookPro16,3` (difiere del iMac20,1 actual; a evaluar si HDMI sigue sin funcionar).
- boot-args: `-btlfxallowanyaddr npci=0x3000 alcid=3 revblock=media revpatch=cpuname,memtab,sbvmm`.
- Booter Quirks: legacy (`RebuildAppleMemoryMap=False`, `SetupVirtualMap=False`,
  `SyncRuntimePermissions=False`, `EnableWriteUnprotector=True`). Nota: la sesión 11 aplicó
  el esquema MODERNO (Otus9051); si cuelga tras ExitBootServices, revertir a legacy.
- Kexts: NootedRed ON, ForgedInvariant, SIN `SMCAMDProcessor`/`AMDRyzenCPUPowerManagement`.
- Confirma que el patrón pantalla interna negra + HDMI funcional es normal para este hardware.

### Referencia nueva: kext IntelMKLFixup (presente en azurejelly, ausente en este EFI)
- Parchea la Intel Math Kernel Library (usada por algunas apps del sistema y apps de terceros)
  para CPUs AMD; evita crashes al detectar instrucciones no soportadas.
- **Estado actual:** no incluido. No es bloqueante para el instalador.
- **Acción futura:** evaluar en fase post-instalación si se observan crashes inexplicables
  en apps (especialmente apps que usan aceleración numérica: Final Cut, Logic, etc.).

### Kext desactualizado: ForgedInvariant v1.2.0 — actualizar a v1.5.0
- La versión instalada es **v1.2.0**. La versión upstream (ChefKissInc, Nov 2024) es **v1.5.0**.
- Mejoras de v1.5.0: "sync to max value across all threads" y "sync early on processPatcher
  instead of IOService::start" — mejor sincronización TSC en arranque temprano.
- **Acción:** actualizar antes del próximo arranque de prueba. Descargar de
  `https://github.com/ChefKissInc/ForgedInvariant/releases` y reemplazar el `.kext` en
  `EFI/OC/Kexts/`; regenerar con el generador y revalidar con ocvalidate.

### Alerta de flujo de trabajo: NO editar config.plist directamente
- Durante la sesión 11, `config.plist` fue editado manualmente (NootedRed `Enabled=false`,
  `-radvesa`) sin pasar por el generador.
- **CRITICO:** el próximo `python3 scripts/05_generate_config.py` SOBREESCRIBIRÁ esos cambios.
- Regla operativa: SIEMPRE usar los toggles del generador (`USE_NRED_NO_ACCEL`, `USE_NRED_DP_DELAY`,
  `USE_MINIMAL_ACPI_FOR_FB_TEST`) y regenerar. NUNCA editar el plist directamente.

### Deuda técnica: NootedRed bug #429 — sleep/wake (FW Injection V2)
- La versión v1.0.0 milestone de NootedRed tiene abierto el bug #429: sleep/wake regresó
  con FW Injection V2 (la arquitectura de inyección de firmware del GPU usada desde ~v0.9).
- **Impacto actual:** ninguno (aún no hemos llegado a la fase de post-instalación).
- **Impacto futuro:** si el objetivo incluye sleep/wake funcional, este bug es un bloqueador
  potencial. Revisar el estado del issue cuando se alcance la fase de puesta a punto
  post-instalación. No diagnosticar como problema propio del EFI.

### Deuda técnica: audio HDMI/DP NO funcional (NootedRed bug #225)
- NootedRed bug #225 ("no audio playback via HDMI/DP") sigue abierto en el milestone v1.0.0
  sin fecha de resolución para el hardware Renoir/Lucienne.
- **Impacto:** el audio por HDMI o DisplayPort no funcionará con NootedRed en este equipo
  hasta que se resuelva upstream. Es una limitación conocida del kext, no un fallo del EFI.
- **Regla:** no diagnosticar "audio HDMI no suena" como problema de este EFI ni de la
  configuración de AppleALC. El audio analógico interno (ALC236, alcid a determinar) es
  independiente y sí es alcanzable.

### Procedimiento operativo: recuperar arranque UEFI tras formateo del USB
El firmware HP 245 G8 NO puede usar `LauncherOption=Full/Short` (el Bootstrap falla en este
firmware; ver cont. 10). El arranque funcional usa una entrada UEFI directa a OpenCore.efi.

**Tras cualquier `mkfs.vfat` del USB o pérdida de la entrada NVRAM:**
```bash
# 1. Sincronizar EFI/ completo (incluye instalador si aplica)
./scripts/06_sync_usb_efi.sh   # o con MOUNT_POINT= si el label no es MACOS

# 2. Restaurar instalador (si se borró con mkfs)
# Copiar la carpeta com.apple.recovery.boot/ de Ventura a la raíz del USB
# (NO usar el cache recovery/ de Sequoia en recovery_sequoia/ — board Mac-937A206F2EE63C01)

# 3. Crear entrada UEFI directa (ejecutar UNA VEZ por reformateo; /dev/sdb = USB)
sudo efibootmgr -c -d /dev/sdb -p 1 -L "OpenCore-HP245" -l '\EFI\OC\OpenCore.efi'
# Verificar que aparece como Boot0000* y primero en BootOrder:
efibootmgr -v | head -20
```
- La entrada de efibootmgr referencia el USB por GUID GPT, no por device node → funciona
  en cualquier puerto USB.
- Si el USB se reformatea, el GUID cambia → la entrada queda huérfana → repetir el paso 3.
- `LauncherOption` debe permanecer en `Disabled` (no crear entradas NVRAM autorreferenciales).

### Estado del generador al cierre de sesión 2026-05-31
- **SMBIOS:** iMac20,1 (`Mac-CFF7D910A743CAAF`) — vigente.
- **Booter Quirks:** esquema MODERNO (Otus9051). Revertir a legacy si cuelga en ExitBootServices.
- **Kexts:** 18 kexts, power AMD real (AMDRyzenCPUPowerManagement + SMCAMDProcessor v1.6.0).
- **ForgedInvariant:** v1.2.0 instalado — PENDIENTE actualizar a v1.5.0.
- **boot-args:** `-v keepsyms=1 debug=0x100 npci=0x3000 alcid=13`.
- **config.plist en disco:** puede tener ediciones manuales de la sesión 11 que el generador
  sobreescribirá en el próximo run. Ejecutar el generador antes de la próxima prueba.

---

## Sesión 2026-05-31 (cont. 12) — HITO: Recovery de macOS Ventura arranca

### Hito confirmado
El instalador de macOS Ventura **arrancó exitosamente** en el HP 245 G8 por primera vez.
Secuencia de arranque observada: líneas blancas de verbose → logo Apple → pantalla del
Recovery de macOS Ventura. El sistema llega completamente al entorno del instalador.

### Configuración exacta que funcionó

- **SMBIOS:** iMac20,1 (`Mac-CFF7D910A743CAAF`) — recomendado por ChefKiss para NootedRed en Renoir/Lucienne.
- **NootedRed:** v0.8.10, **Enabled=True**. Sin DeviceProperties para la iGPU (vacío).
- **ForgedInvariant:** v1.5.0 (TSC sync; actualizado desde v1.2.0 antes de esta prueba).
- **AMDRyzenCPUPowerManagement:** **Disabled** (kext desactivado).
- **SMCAMDProcessor:** **Disabled** (kext desactivado).
- **DummyPowerManagement:** **True** (power management estándar AMD sin kexts especializados).
- **Booter Quirks:** esquema **moderno** (Otus9051):
  `RebuildAppleMemoryMap=True`, `SetupVirtualMap=True`, `SyncRuntimePermissions=True`,
  `EnableWriteUnprotector=False`, `DevirtualiseMmio=True`, `ProtectUefiServices=True`.
- **ACPI:** 10 SSDTs (EC, GPRW, USBX, PLUG-ALT, XOSI, PNLF, ALS0, PMC, HPET, USB-Reset)
  + parche GPRW→XPRW. SSDT-PLUG-ALT.aml = versión AMD (no la Intel estándar).
- **boot-args:** `-v keepsyms=1 debug=0x100 npci=0x3000 alcid=13 -NRedDPDelay`
  (`-NRedDPDelay` retrasa el link-training del panel eDP interno).
- **Cadena de arranque:** entrada UEFI directa a `\EFI\OC\OpenCore.efi` vía efibootmgr
  (el Bootstrap de OpenCore falla en este firmware HP; `LauncherOption=Disabled`).
- **USB:** puerto USB 2.0 (negro), pendrive con `com.apple.recovery.boot/` de Ventura 13
  (`Mac-4B682C642B45593E`, BaseSystem.dmg 706568592 B).

### Problema: teclado interno y touchpad no funcionan en el Recovery

- **Síntoma:** una vez en el Recovery de macOS, el teclado interno y el touchpad del portátil
  **no responden**. No es posible interactuar con el instalador usando los dispositivos del chasis.
- **Solución temporal confirmada:** un **ratón USB externo SÍ funciona** en el Recovery. Con él
  se puede navegar la interfaz del instalador y proceder con la instalación de macOS.
- **Causa probable:** VoodooPS2Controller (el kext que gestiona teclado/touchpad PS/2 en este
  portátil) no está correctamente configurado para el hardware PS/2 concreto del HP 245 G8,
  o requiere un SSDT adicional (p.ej. SSDT-PS2K para el mapeo de teclas), o hay una colisión
  con la inicialización del controlador PS/2 real del chasis. El teclado/touchpad del HP 245 G8
  se comunica por I2C o por PS/2 — verificar en la DSDT el path del controlador.
- **No es bloqueante para la instalación:** con el ratón USB externo se puede completar la
  instalación de macOS. El teclado/touchpad se afina en fase post-instalación.

### Próximos pasos

1. **[USUARIO — inmediato]** Completar la instalación de macOS Ventura usando el ratón USB
   externo. Seleccionar disco destino (NVMe Kingston NV3), iniciar la instalación y esperar
   el proceso de copia + reinicios. Usar siempre el USB en puerto USB 2.0.

2. **[YO — investigar VoodooPS2Controller]** Tras la instalación, diagnosticar el teclado/touchpad:
   - Verificar en `docs/DSDT.dsl` si el controlador PS/2 está bajo `\_SB.PCI0.SBRG.PS2K` o
     si el teclado es realmente I2C (VoodooI2C en lugar de VoodooPS2).
   - Comparar con el EFI de Otus9051 (5300U exacto): ¿usa VoodooPS2 o VoodooI2C?
   - Comparar con azurejelly (HP 245 G8, mismo chasis): su configuración de input devices.
   - Si es PS/2 real: añadir SSDT-PS2K o VoodooPS2Controller versión compatible con el
     controlador Synaptics/ELAN del HP 245 G8.
   - Si es I2C: reemplazar VoodooPS2 por VoodooI2C + VoodooI2CHID.

3. **[Deuda técnica post-instalación]** Una vez macOS instalado y arrancando desde disco:
   - USB mapping real con UTBMap (USBToolBox en macOS, no el UTBDefault genérico).
   - Audio ALC236: probar layouts alternativos a `alcid=13` si el audio no funciona.
   - Evaluar kext `IntelMKLFixup` (presente en azurejelly) para evitar crashes en apps AMD.
   - Evaluar `AMDRyzenCPUPowerManagement` + `SMCAMDProcessor` con `DummyPowerManagement=False`
     una vez el sistema esté estable (mejora la gestión de frecuencia/temperatura).
   - Pantalla interna (eDP): si sigue negra tras instalar, investigar SSDT-eDP o parámetros
     de link-training de NootedRed para el panel 1366x768 de Lucienne.
   - Actualizar ForgedInvariant si sale versión posterior a v1.5.0.

## Sesión 2026-06-02 (cont. 13) — HITO: macOS Ventura INSTALADO y arrancando sin USB

**Resultado:** macOS Ventura 13 quedó instalado en el HDD interno (`sda2`, convertido a APFS por
el instalador) y el equipo arranca desde el EFI del disco interno (`sda1`) **sin la USB**. El
dual boot con Arch Linux (NVMe Kingston, LUKS) quedó intacto. Teclado y touchpad internos
funcionan en el sistema instalado.

**Qué destrabó la instalación (acumulado de las sesiones previas):**
1. **USB reconstruido desde cero y limpio** (`07_rebuild_usb.sh`): `wipefs -a` eliminó una firma
   `iso9660` residual (el pendrive fue antes un USB de Debian) que el `parted` no borraba y que
   confundía al firmware HP. Copia con `cp` (no `rsync -a`, que falla en FAT32 por el chown) y
   solo los `.aml` de ACPI.
2. **Quirks alineados con Otus9051** (mismo CPU 5300U, funcional): `DevirtualiseMmio`,
   `ProtectUefiServices`, `DisableIoMapper`, `LapicKernelPanic` = **False** (estaban en True).
3. **`agdpmod=pikera`** añadido (lo usa el Lenovo V15 G2, mismo CPU).
4. **`-NRedNoAccel` manual en el picker** durante la fase de copia/sellado para saltar el muro
   del framebuffer Vega 6. Es un flag de instalación: NO va en el config (la aceleración Metal
   se necesita en uso normal).

**Sobre el error previo `OCB: LoadImage failed - Unsupported`:** era el instalador *staged* en el
HDD (`boot.efi` truncado por los apagados forzados durante los freezes), no el config. Se resolvió
reconstruyendo el USB limpio y haciendo **Erase** del volumen destino antes de reinstalar.

**Copiar el EFI al disco interno:** se usó **MountEFI** (chris1111,
<https://github.com/chris1111/MountEFI>) para montar ambos ESP (USB e interno) y copiar la carpeta
`EFI/` de la USB al disco interno. OJO: hay dos volúmenes EFI (`/Volumes/EFI` y `/Volumes/EFI 1`);
el comando `cp -R /Volumes/EFI/EFI /Volumes/EFI/` (sugerido por un asistente externo) es **erróneo**
(copia la EFI sobre sí misma).

### Pendiente — post-instalación (ver guía Dortania para AMD/post-install)

1. **Aceleración iGPU completa:** verificar en "Acerca de este Mac" que la Vega 6 reporta VRAM y
   que Metal funciona. Si la UI va por CPU o falta aceleración, revisar NootedRed (boot-args,
   SMBIOS, `revblock`/`revpatch` de RestrictEvents) — el `-NRedNoAccel` NO está en el config.
2. **Audio:** probar `alcid=13` real (altavoces/auriculares); si falla, layouts alternativos.
3. **USB mapping real:** sustituir `UTBDefault` por un mapa propio con USBToolBox desde macOS.
4. **Power management AMD:** reevaluar `AMDRyzenCPUPowerManagement` + `SMCAMDProcessor` con
   `DummyPowerManagement=False` una vez el sistema esté estable.
5. **Limpiar boot-args:** para uso diario, considerar quitar `-v debug=0x100 keepsyms=1`.
6. **WiFi RTL8822CE:** no soportado en macOS — dongle USB-Ethernet/WiFi (ver `wifi_rtl8822ce.md`).
7. **Sonoma/Sequoia:** evaluar actualización (NootedRed soporta versiones nuevas; requiere OpenCore
   y NootedRed recientes). NO usar "Software Update" directo — hacer USB nueva y update controlado.

## Plan de post-install (investigado 2026-06-02, workflow Dortania + NootedRed + AMD-OSX)

Regla transversal: **un solo cambio por arranque**, `ocvalidate` antes de sincronizar, y **backup
del EFI que ya arranca** antes de tocar nada (`cp -r EFI EFI_OK_ventura`). El EFI vivo es el del
disco interno (`sda1`); los cambios del generador llegan ahí copiando el `config.plist` al ESP
interno (MountEFI desde macOS, o montando `sda1` desde Arch).

### Diagnóstico de la iGPU — "falta aceleración"
- **Causa #1 (más probable): UMA Frame Buffer bajo en BIOS (512 MB) → sin Metal.** NootedRed exige
  ≥512 MB y **1 GB+ para acelerar de verdad**. Síntoma: "Acerca de este Mac" muestra la GPU con
  VRAM ridícula (~7 MB) y sin nombre = estás en VESA/fallback, no Metal. **Se arregla en BIOS**
  (subir UMAF a ≥1 GB; si HP no lo expone, **Smokeless_UMAF**), NO en el config.
- **Verificar primero** (antes de cambiar nada):
  - "Acerca de este Mac" / Información del Sistema → Gráficos: debe listar "AMD Radeon ... Renoir/
    Raven Graphics" con la VRAM asignada.
  - `system_profiler SPDisplaysDataType | grep -i "Metal\|VRAM\|Chipset"`
  - `ioreg -l | grep -i "MetalPluginName\|IOAccelerator"` → presentes = aceleración real.
- **NO añadir DeviceProperties al iGPU** (rompe NootedRed). Dejar `DeviceProperties>Add` vacío.
- **`revblock=media`** (arg de RestrictEvents) añadido a boot-args — mejora estabilidad/aspecto.
- **Limitaciones permanentes de NootedRed (no son fallos a arreglar):** sin VCN/DRM (decodificación
  HW de vídeo, issue #28), sin audio por HDMI, sleep/wake no fiable. Transversales a Ventura/Sonoma/Sequoia.

### Pasos por prioridad
1. **iGPU:** BIOS UMAF ≥1 GB (Smokeless_UMAF si no se expone) + `revblock=media` (ya en config). Verificar Metal.
2. **Audio:** `alcid=13` ya puesto (funcional en Otus9051). Si falla, bisecar `alcid=` (uno por arranque):
   `3 → 13 → 11 → 12 → 14 → 15 → 19 → 23`. Al acertar, migrar a `layout-id` en DeviceProperties del HDEF y quitar `alcid=`.
3. **USB mapping:** reemplazar `UTBDefault` por `UTBMap.kext` real. Mapear con USBToolBox/tool desde
   **Windows** (companion, no depende de SMBIOS) o **USBMap (corpnewt)** desde macOS. Máx **15 puertos**
   por controlador. Orden: `USBToolBox.kext` antes de `UTBMap.kext`; eliminar `UTBDefault`.
4. **Power management AMD: DEJAR OFF** (DummyPowerManagement=True + kexts OFF). Panic confirmado con
   `AMDRyzenCPUPowerManagement v0.7.2 + DummyPM=False` (Caps Lock). Experimentar solo en copia del EFI.
5. **Limpiar boot-args de debug** (cuando todo funcione): quitar `-v keepsyms=1 debug=0x100`.
   Objetivo diario aprox.: `npci=0x3000 alcid=13 revblock=media -NRedDPDelay` (+`agdpmod=pikera` solo si HDMI externo).
6. **SIP/Security:** `SecureBootModel=Disabled` (kexts sin firmar) — dejar. `csr-active-config`:
   mantener `03080000` mientras se tocan kexts; subir a `00000000` (SIP completo) cuando se estabilice.
   `ScanPolicy=0`: dejar (muestra USB/Recovery/Linux en el picker).
7. **Arranque sin USB:** ya blessed (arranca del HDD). **Dejar `LauncherOption=Disabled`** (cambiarlo
   reintrodujo el bucle "Already Started"); el firmware arranca por fallback `\EFI\BOOT\BOOTx64.efi`
   (Bootstrap 24K). Opcional `BootProtect=Bootstrap` si algo pisa el BOOTx64. No tocar el NVMe (Arch).

### Decisión de versión: QUEDARSE EN VENTURA 13
- Ventura es la versión **más rodada** para Renoir/Lucienne con NootedRed (las refs del mismo CPU
  están calibradas aquí). **Sonoma** = movimiento lateral (crashes/bootloop propios: issues #194/#257/#286).
  **Sequoia** = experimental ("crashes; no daily driver" según el repo). Nada que falta mejora al subir.
- Si en el futuro hay que subir: **USB instalador nuevo, NUNCA Software Update directo**; mantener el
  EFI/instalación de Ventura como fallback. NootedRed 0.8.10 (ya lo tenemos) sirve hasta macOS 26;
  OpenCore último 1.0.x; AMD_Vanilla actualizado (solo Sequoia: activar su parche PAT y desactivar el previo).

## Verificación post-install 2026-06-02 — iGPU ACELERADA + causa raíz del brillo

**iGPU CONFIRMADA con aceleración completa** (en el sistema instalado):
```
system_profiler SPDisplaysDataType:
  AMD Radeon RX Renoir Graphics
  VRAM (Total): 2 GB
  Metal Support: Metal 3
```
→ El UMA Frame Buffer YA está en 2 GB (la BIOS está bien, NO hace falta Smokeless_UMAF) y Metal 3
funciona. **No falta nada de aceleración gráfica.** Los comandos que "fallaron" del usuario eran
typos (`PerfromanceStatistics`, `NooteRed`). En macOS reciente `kextstat` está deprecado; usar
`kmutil showloaded | grep -i NootedRed`.

**Único pendiente real = control de brillo (slider ausente). CAUSA RAÍZ confirmada en código fuente
de NootedRed** (`Backlight.cpp:87-91`): NootedRed solo instala el subsistema de backlight si
`modelType == ComputerLaptop`, y Lilu (`kern_devinfo.cpp`) marca Laptop SOLO si el identificador
SMBIOS contiene la cadena **"Book"**. Con **`iMac20,1`** (sin "Book") → NootedRed lo trata como
desktop y hace `return` sin registrar el backlight. Por eso no hay slider pese a que la GPU acelera.

- **Fix aplicado (opción A, mínima y reversible):** `AMDBacklight=1` en boot-args — override exacto
  del propio código (`PE_parse_boot_argn("AMDBacklight", ...)`), mantiene iMac20,1 y el UUID estable.
- **Alternativa B (probada en Otus9051, mismo CPU):** SMBIOS **MacBookPro16,2** activa el flag laptop
  solo, sin AMDBacklight ni -NRedDPDelay (pero regenera SystemUUID/ROM/serial).
- **SSDT-PNLF: el nuestro es el correcto** (idéntico al de Otus9051: OEM VISUAL/AMDPNLF, `_HID APP0002`,
  `_CID backlight`). En Renoir NootedRed controla el brillo por software (`dc_link_set_backlight_level`),
  no necesita `_BCM`/`_BCL` ni PWMMax.
- **Issue #302** (Renoir, brillo) está CERRADO/resuelto con SSDT-ALS0 (que ya tenemos). El soporte de
  brillo en Renoir está implementado, no es limitación abierta.

**Consejos externos (Google IA) que NO aplican a este equipo:** quitar WhateverGreen (no lo tenemos),
limpiar DeviceProperties del iGPU (ya vacío), añadir SSDT-PNLF/BrightnessKeys/SMCLightSensor (ya están).
Toda la parte de "Intel + Lilu + WhateverGreen + OCLP" es de hackintosh Intel — irrelevante para AMD/NootedRed.

**Limpiezas opcionales detectadas (no urgentes, probar por separado):** `agdpmod=pikera` es redundante
(NootedRed ya parchea AGDP internamente, `Hotfixes/AGDP.cpp`); `-NRedDPDelay` no lo usa la referencia
del mismo CPU (es para black-screen por link-training, no para brillo) — si el panel enciende bien, se
puede probar a quitarlo.

### Boot-args reales de NootedRed (confirmados en código fuente, v0.8.10)
`-NRedOff`, `-NRedDebug`, `-NRedBeta`, `-NRedNoAccel`, `-NRedDPDelay`, `-NRedDelayPanic`,
`-NRedDebugUltra`, `-NRedCursorDebug`, y `AMDBacklight=<bool>`. `revblock`/`revpatch` NO son de
NootedRed (son de RestrictEvents).

## RESULTADO 2026-06-02 — sistema FUNCIONAL ✅

Tras aplicar `AMDBacklight=1` al EFI del disco interno (vía MountEFI) + Reset NVRAM, el usuario
confirma en macOS Ventura:
- ✅ **Brillo**: el slider funciona (causa raíz era el SMBIOS sin "Book"; `AMDBacklight=1` lo resolvió).
- ✅ **Audio**: funciona (ALC236, `alcid=13`).
- ✅ **Batería**: lectura correcta (SMCBatteryManager).
- ✅ **iGPU**: acelerada (2 GB VRAM, Metal 3) — ya confirmado antes.
- ✅ **Teclado/touchpad** internos, arranque sin USB.

**boot-args finales (en uso):** `-v keepsyms=1 debug=0x100 npci=0x3000 alcid=13 agdpmod=pikera
revblock=media AMDBacklight=1 -NRedDPDelay`. SMBIOS `iMac20,1`. AMD PM kexts OFF + DummyPM=True.

**Pendientes (no bloqueantes):** WiFi RTL8822CE (no soportado → dongle USB), USB mapping real con
USBToolBox, limpiar `-v debug=0x100 keepsyms=1` para uso diario. **Versión: se queda en Ventura.**

## Refactor 2026-06-02 — 3 perfiles de EFI + identidad fija

El generador `05_generate_config.py` pasa a soportar `--profile {install,stable,postinstall}`
(y `--all`). Diseño: **un solo árbol** de kexts/SSDTs; cada perfil es un `config.plist` distinto
guardado en `EFI/OC/profiles/config-<perfil>.plist`; el activo (`EFI/OC/config.plist`) es el que
sincroniza el script 06. OpenCore solo carga lo declarado en cada config, así que no hace falta
duplicar carpetas EFI.

- **install / stable:** verbose+debug (`-v keepsyms=1 debug=0x100`), Target=67 (log a ESP),
  Timeout=0, UTBDefault, SetApfsTrimTimeout=-1. `stable` = ancla del EFI que arranca hoy
  (verificado bit-a-bit idéntico al config previo: anti-regresión).
- **postinstall:** sin verbose/debug, Target=3, Timeout=5 (auto-arranca), **+ECEnabler.kext**
  (batería fiable tras wake) **+SSDT-RTCAWAC.aml** (RTC/sleep), SetApfsTrimTimeout=**0** (HDD sin
  TRIM), y **UTBMap** si existe (si no, mantiene UTBDefault y avisa).
- **Identidad FIJA:** `SystemUUID` y `ROM` pasan de regenerarse aleatoriamente en cada run a ser
  **constantes** (los del config que funciona) — evita romper iMessage/iCloud/NVRAM entre regens.
- **AMD PM:** OFF en los 3 perfiles. Causa raíz del panic documentada: P-states legacy por MSR sin
  CPPC en la APU Lucienne móvil (no es de versión). El SMU del firmware ya gobierna con DummyPM=True.
- **ECEnabler 1.0.5** (de hp-245-g8-efi-base) y **SSDT-RTCAWAC** (de otus9051) copiados al árbol EFI.
  Quedan disponibles pero solo el perfil postinstall los declara.
- **RealtekRTL8111 2.4.2** (de hp-245-g8-efi-base) añadido al perfil postinstall. El puerto RJ45 de
  este equipo se dañó (corto por tormenta) y no aparece en `lspci` (desconectado del bus PCI), así
  que el kext no engancha nada y queda inactivo — inofensivo. Se deja listo por si se repara/reemplaza
  el puerto. NO revive hardware muerto. (La WiFi RTL8822CE sigue sin soporte nativo → dongle USB.)

Los 3 perfiles validan con ocvalidate (0 errores). USB mapping real (`UTBMap.kext`) sigue pendiente
de generar en macOS con USBMap/USBToolBox enchufando dispositivos en cada puerto físico.

## Auditoría de kexts 2026-06-02 — guía oficial ChefKiss + 4 subagentes + EFIs de referencia

Investigación exhaustiva (guía oficial de ChefKiss clonada de `git.chefkiss.dev/ChefKiss/Website`
→ `kexts.mdx`, + foros AMD-OSX/r-hackintosh, + repos azurejelly/beitanam/Otus9051). Conclusión: el
stack ya está completo; casi nada genuino que añadir. Cambios aplicados al perfil **postinstall**:

- **Quitado `SMCSuperIO`** — la guía oficial dice literal *"Do NOT use on AMD"* (monitoriza fans;
  en AMD no aplica). Estaba ON por inercia. Fuera en postinstall.
- **Quitado `AppleALCU`** — subconjunto digital de AppleALC con `MinKernel 23.0.0` (Sonoma): en
  Ventura ni cargaba, y el audio HDMI no funciona con NootedRed. Redundante. Solo AppleALC.
- **Añadido `revpatch=cpuname`** a boot-args — nombre real del CPU en "Acerca de este Mac"
  (RestrictEvents, guía oficial). Cosmético, seguro. Junto a `revblock=media`.

Mecanismo nuevo en el generador: campos `extra_args` y `remove_kexts` por perfil (la limpieza solo
toca postinstall; stable/install quedan intactos como ancla).

**Sensores y micrófono — AÑADIDOS 2026-06-02 (a petición):**
- `SMCRadeonSensors 2.4.0` (ChefKissInc) — temperatura del iGPU AMD. **Añadido al perfil postinstall.**
- `SMCProcessorAMD 1.0.1` (**macos86**, fork standalone) — temperatura del CPU AMD. **Añadido al
  perfil postinstall.** OJO: Lorys89 (que enlaza la guía) está vacío/muerto; se usa el fork de macos86,
  que NO depende de AMDRyzenCPUPowerManagement (a diferencia del SMCAMDProcessor de trulyspinach, que
  reintroduce el panic). Ambos son plugins de VirtualSMC, solo lectura — NO tocan power management.
- `AMDMicrophone 1.0.0` (qhuyduong) — micrófono interno digital (ACP) de Renoir. **Guardado en
  `macos/extras/` (NO por OpenCore)**; se instala en `/Library/Extensions/`. Nuestro `csr=03080000`
  ya incluye `CSR_ALLOW_UNTRUSTED_KEXTS`, así que NO hay que relajar más el SIP. Guía:
  `macos/extras/README.md`. Solo si se necesita el micro interno.

**Descartados (NO aplican a este hardware/Ventura), confirmado por guía + agentes:** FeatureUnlock
(requiere iGPU Intel), CryptexFixup (no-op con AVX2 de Zen2), AMFIPass (no desactivamos AMFI),
NoTouchID (corregido desde Big Sur), CpuTopologyRebuild (solo Intel híbrido), CpuTscSync/AmdTscSync
(conflicto con ForgedInvariant), HibernationFixup (sleep roto por NootedRed #429 + HDD), VoodooRMI
(es para Synaptics; nuestro touchpad es ELAN por HID), GenericUSBXHCISB (no tenemos el cuelgue USB),
y todos los de WiFi/BT/Ethernet de otro hardware (Intel/Broadcom/RTL distinto). NootedRed: nunca con
WhateverGreen y NUNCA DeviceProperties al iGPU (verificado: DeviceProperties>Add vacío).

