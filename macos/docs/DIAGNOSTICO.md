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
