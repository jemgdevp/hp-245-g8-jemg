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
