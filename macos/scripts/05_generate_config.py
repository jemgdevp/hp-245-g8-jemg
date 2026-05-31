#!/usr/bin/env python3
"""
OpenCore config.plist generator for AMD Ryzen 3 5300U (Lucienne/Renoir Zen 2 APU).
Target: macOS Ventura 13 (or newer), SMBIOS iMac20,1 (receta Otus9051 exact-CPU + ChefKiss NootedRed prereqs).
See macos/docs/DIAGNOSTICO.md for full bisection history.
"""

import os
import sys
import plistlib
import subprocess
import uuid
import random
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EFI_OC = PROJECT_ROOT / "EFI/OC"
TOOLS = PROJECT_ROOT / "tools"
TEMPLATE_PATH = EFI_OC / "config.plist"
AMD_VANILLA_DIR = TOOLS / "AMD_Vanilla"
AMD_VANILLA_REPO = "https://github.com/AMD-OSX/AMD_Vanilla.git"

# SMBIOS MacBookPro16,2: recomendado por ChefKiss para NootedRed en Renoir/
# Lucienne. MacBookPro16,3 NO está en su lista y tiene crash documentado del
# framebuffer (negro + reinicio tras ExitBootServices). Serial validado con
# tools/.../macserial --model MacBookPro16,2.
SERIAL = "C02DH0E0PN6P"
MLB = "C02038201LDPN6P1H"
SMBIOS_MODEL = "iMac20,1"
BOARD_ID = "Mac-CFF7D910A743CAAF"  # board-id oficial de iMac20,1 (receta Otus, 5300U)

# Núcleos físicos del Ryzen 3 5300U (4C/8T). Se inyecta en los patches
# AMD_Vanilla "cpuid_cores_per_package to constant"; dejarlo en 0 cuelga
# el arranque SMP/PCI.
PHYSICAL_CORES = 4

KEXTS = [
    ("Lilu",        "x86_64", "",      "",      False),
    # Codeless: evita panics de AppleMCEReporter en AMD ≥ macOS 12.3
    ("AppleMCEReporterDisabler", "x86_64", "", "", True),
    ("VirtualSMC",  "x86_64", "",      "",      False),
    # ForgedInvariant: TSC-sync de ChefKiss (reemplaza AmdTscSync). El TSC
    # desincronizado cuelga la fase tardía del arranque (AppleCredentialManager/
    # AppleKeyStore). Lo usa el EFI de referencia del mismo HP 245 G8.
    ("ForgedInvariant", "x86_64", "",  "",      False),
    # Power management AMD real (receta Otus9051, el EFI del 5300U que arranca):
    # sustituyen a DummyPowerManagement=True. Dependen de Lilu+VirtualSMC.
    ("SMCAMDProcessor", "x86_64", "", "", False),
    ("AMDRyzenCPUPowerManagement", "x86_64", "", "", False),
    ("SMCBatteryManager", "x86_64", "", "",    False),
    # SMCProcessor (Intel-only) y SMCDellSensors (Dell) eliminados: inútiles/
    # ruidosos en un HP con Ryzen; el log rechazaba SMCDellSensors.
    ("SMCSuperIO",     "x86_64", "",    "",     False),
    ("SMCLightSensor", "x86_64", "",    "",     False),
    # NootedRed NO se desactiva durante la instalación: Renoir/Lucienne NO tiene
    # framebuffer básico en macOS; sin este kext no hay imagen tras ExitBootServices
    # (pantalla negra). El generador lo deja Enabled=True como todos; el 5º campo es
    # noexec (False = tiene binario en Contents/MacOS, no es codeless).
    ("NootedRed",      "x86_64", "",    "",     False),
    ("AppleALC",       "x86_64", "",    "",     False),
    ("AppleALCU",      "x86_64", "23.0.0", "", False),
    ("USBToolBox",     "x86_64", "",    "",     False),
    ("UTBDefault",     "Any",    "",    "",     True),
    ("VoodooPS2Controller", "x86_64", "", "",   False),
    ("NVMeFix",        "x86_64", "",    "",     False),
    ("BrightnessKeys", "x86_64", "",    "",     False),
    ("RestrictEvents", "x86_64", "",    "",     False),
]

# boot-args alineados con el EFI de referencia del MISMO modelo (HP 245 G8) + Otus9051 (exact 5300U que arranca):
#   -v keepsyms=1 debug=0x100  → verbose + símbolos en panics (diagnóstico)
#   npci=0x3000                → evita el cuelgue en [PCI configuration begin]
#                                (BIOS HP sin opción Above4G accesible; Dortania AMD Zen confirma)
#   alcid=13                   → layout audio Realtek ALC236 (probado en Otus 5300U + ChefKiss)
#   -NRedDPDelay               → NootedRed: retrasa el link-training del panel interno (eDP).
#                                Arregla black screen / framebuffer hang en muchos Renoir/Lucienne
#                                con paneles eDP (común en laptops HP). Ver ChefKiss FAQ + issues.
#                                (Estaba documentado pero ausente en la versión post-Otus; live config lo confirma.)
#   (Test) -NRedNoAccel        → Deshabilita aceleración Metal temporalmente (útil para aislar).
#                                Reversible; quitar una vez funcione el FB.
#
# Fuentes indexadas (esta sesión + DIAGNOSTICO):
#   - ChefKiss NootedRed (chefkiss.dev/applehax/nootedred): Vega Raven full (5300U Lucienne OK),
#     SMBIOS iMac20,1/MacBookPro16,2/iMacPro1,1, VRAM 1GiB+, NootedRed 0.8.10 latest (May 2026),
#     backlight: SSDT-PNLF+ALS0 + SMCLightSensor + BrightnessKeys (todos presentes).
#   - Dortania AMD Zen: npci=0x3000 para HP sin Above4G, DeviceProperties iGPU vacío OK para la mayoría.
#   - Otus9051: mismo CPU exacto, external HDMI funciona, alcid=13.
# Fácil toggle para bisección de NootedRed framebuffer (ver image5 + DIAGNOSTICO)
USE_NRED_DP_DELAY = True
_NRED_EXTRA = " -NRedDPDelay" if USE_NRED_DP_DELAY else ""
BOOT_ARGS = "-v keepsyms=1 debug=0x100 npci=0x3000 alcid=13" + _NRED_EXTRA
# Cpuid1Data VACÍO: en AMD los parches AMD_Vanilla ya fijan la familia de CPU.
# Inyectar un Cpuid1Data spoofeado de Intel ENCIMA de esos parches provoca un
# kernel panic tempranísimo (negro + reinicio sin verbose). El EFI de referencia
# del mismo HP 245 G8 arranca con Cpuid1Data/Mask vacíos.
CPUID1_DATA = b""
CPUID1_MASK = b""
import base64

CSR_ACTIVE = base64.b64decode("AwgAAA==")
DISPLAY_ALL = 2147483714
LOG_SERIAL_FILE = 67

def generate_rom():
    result = bytearray(6)
    for i in range(6):
        d = random.randint(0, 255)
        if i == 0:
            d &= 0xFE
        result[i] = d
    return bytes(result)


def clone_amd_vanilla():
    if AMD_VANILLA_DIR.exists():
        print("  Updating AMD_Vanilla...")
        subprocess.run(["git", "-C", str(AMD_VANILLA_DIR), "pull", "--ff-only"],
                       capture_output=True)
    else:
        print("  Cloning AMD_Vanilla...")
        subprocess.run(["git", "clone", AMD_VANILLA_REPO, str(AMD_VANILLA_DIR)],
                       capture_output=True, check=True)


def load_amd_patches():
    candidates = sorted(AMD_VANILLA_DIR.glob("*.plist"))
    if not candidates:
        return []

    preferred = [
        p for p in candidates
        if any(k in p.name.lower() for k in ("sonoma", "14"))
    ] or [p for p in candidates if p.name.lower() == "patches.plist"]
    if not preferred:
        preferred = [candidates[-1]]

    patch_file = preferred[0]
    print(f"  Loading patches from: {patch_file.name}")

    data = plistlib.loads(patch_file.read_bytes())
    kernel = data.get("Kernel", {})

    patches = [
        {
            "Arch": rp.get("Arch", "Any"),
            "Base": rp.get("Base", ""),
            "Comment": rp.get("Comment", "AMD Vanilla patch"),
            "Count": rp.get("Count", 0),
            "Enabled": True,
            "Find": rp.get("Find", b""),
            "Identifier": rp.get("Identifier", "kernel"),
            "Limit": rp.get("Limit", 0),
            "Mask": rp.get("Mask", b""),
            "MaxKernel": rp.get("MaxKernel", ""),
            "MinKernel": rp.get("MinKernel", ""),
            "Replace": rp.get("Replace", b""),
            "ReplaceMask": rp.get("ReplaceMask", b""),
            "Skip": rp.get("Skip", 0),
        }
        for rp in kernel.get("Patch", [])
    ]

    # Inyectar el conteo de núcleos en los patches "cpuid_cores_per_package
    # to constant". El placeholder de AMD_Vanilla es el byte tras el opcode
    # mov (b8/ba); dejarlo en 0x00 cuelga el arranque SMP/PCI.
    fixed = 0
    for patch in patches:
        if "cpuid_cores_per_package to constant" in patch["Comment"]:
            repl = bytearray(patch["Replace"])
            if len(repl) >= 2:
                repl[1] = PHYSICAL_CORES
                patch["Replace"] = bytes(repl)
                fixed += 1
    print(f"  cpuid_cores_per_package set to {PHYSICAL_CORES} in {fixed} patch(es)")

    return patches


def kext_entry(name, arch, minkernel, maxkernel, noexec):
    entry = {
        "Arch": arch,
        "BundlePath": f"{name}.kext",
        "Comment": name,
        "Enabled": True,
        "MaxKernel": maxkernel,
        "MinKernel": minkernel,
        "PlistPath": "Contents/Info.plist",
    }
    if not noexec:
        entry["ExecutablePath"] = f"Contents/MacOS/{name}"
    else:
        entry["ExecutablePath"] = ""
    return entry


def build_config():
    print("=" * 60)
    print("  OpenCore config.plist — AMD Renoir + Sonoma")
    print("=" * 60)

    clone_amd_vanilla()
    patches = load_amd_patches()
    print(f"  Kernel patches loaded: {len(patches)}")

    template = plistlib.loads(TEMPLATE_PATH.read_bytes())
    system_uuid = str(uuid.uuid4()).upper()
    rom = generate_rom()
    rom_str = ":".join(f"{b:02x}" for b in rom)

    print(f"  Serial:      {SERIAL}")
    print(f"  MLB:         {MLB}")
    print(f"  SystemUUID:  {system_uuid}")
    print(f"  ROM:         {rom_str}")

    template["ACPI"]["Quirks"]["ResetLogoStatus"] = True

    # === ACPI PROFILE (fácil de cambiar para bisección) ===
    # FULL = tu set validado (10 SSDTs) — produce los AE_ALREADY_EXISTS de image5
    # MINIMAL = más cercano al Otus9051 (mismo 5300U que arranca) —  menos colisiones
    USE_MINIMAL_ACPI_FOR_FB_TEST = False

    if USE_MINIMAL_ACPI_FOR_FB_TEST:
        ACPI_SSDTS = [
            "SSDT-ALS0", "SSDT-EC", "SSDT-PLUG", "SSDT-PNLF",
            "SSDT-USBX", "SSDT-XOSI",
            # Añade "SSDT-RTCAWAC", "SSDT-RMNE" si tu DSDT los necesita
        ]
        print("  [FB TEST] Usando set ACPI MINIMAL estilo Otus (menos colisiones)")
    else:
        # Set completo (tu versión actual, validada contra DSDT)
        ACPI_SSDTS = [
            "SSDT-ALS0", "SSDT-EC", "SSDT-GPRW", "SSDT-HPET", "SSDT-PLUG",
            "SSDT-PMC", "SSDT-PNLF", "SSDT-USBX", "SSDT-XOSI", "SSDT-USB-Reset",
        ]

    # SSDTs reales del HP 245 G8 (copiados del EFI de referencia del mismo modelo,
    # en docs/hp-245-g8-efi-base). Arrancar SIN SSDTs colgaba la enumeración PCI
    # (Couldn't alloc AppleKeyStoreTest / "pci ... flags 0xc000"). El crítico es
    # SSDT-EC (EC válido temprano en SBRG) y el par SSDT-GPRW + parche GPRW->XPRW
    # (neutraliza el instant-wake que cuelga el bus PCI en este chasis HP).
    # SSDT-PLUG (no PLUG-ALT): la DSDT real declara las CPU como Device
    # \_SB.P000 (_HID ACPI0007), no PR00; el PLUG-ALT del EFI de referencia (5500U)
    # apuntaba a PR00 inexistente. SSDT-PLUG.aml se regeneró para P000 (ver
    # acpi_src/SSDT-PLUG.dsl) y se validó contra docs/DSDT.aml.
    # SSDT-USB-Reset: desactiva los RHUB de XHC0/XHC1 bajo Darwin para que macOS
    # re-enumere el USB desde cero. Fix del cuelgue en la enumeración USB/PCI
    # (freeze tras AppleKeyStoreTest). Paths validados contra docs/DSDT.aml:
    # \_SB.PCI0.GP17.XHC0.RHUB y XHC1.RHUB (sin _STA propio -> sin parche XSTA).
    template["ACPI"]["Add"] = [
        {"Comment": s, "Enabled": True, "Path": f"{s}.aml"} for s in ACPI_SSDTS
    ]
    # Find/Replace de 5 bytes (incluye el 0x02 = nº de args del método GPRW) y
    # esquema COMPLETO de ACPI>Patch (Base/BaseSkip/ReplaceMask son obligatorios;
    # sin ellos ocvalidate falla "Missing key Base/BaseSkip/ReplaceMask").
    template["ACPI"]["Patch"] = [{
        "Base": "", "BaseSkip": 0,
        "Comment": "change GPRW to XPRW",
        "Count": 0, "Enabled": True, "Limit": 0,
        "Find": bytes.fromhex("4750525702"), "Replace": bytes.fromhex("5850525702"),
        "Mask": b"", "ReplaceMask": b"",
        "OemTableId": b"", "Skip": 0,
        "TableLength": 0, "TableSignature": b"",
    }]

    # Esquema de memoria "legacy": el que arranca en el firmware del HP 245 G8
    # (confirmado por el EFI de referencia del mismo modelo). El esquema moderno
    # (RebuildAppleMemoryMap/SetupVirtualMap/SyncRuntimePermissions=True) cuelga
    # el kernel justo tras ExitBootServices en esta placa.
    template["Booter"]["Quirks"].update({
        "AvoidRuntimeDefrag": True,
        "DevirtualiseMmio": False,
        "EnableSafeModeSlide": True,
        "EnableWriteUnprotector": True,
        "ProvideCustomSlide": True,
        "SetupVirtualMap": False,
        "SyncRuntimePermissions": False,
        "RebuildAppleMemoryMap": False,
        "ResizeAppleGpuBars": -1,
    })

    template["Kernel"]["Add"] = [
        kext_entry(name, arch, mink, maxk, noex)
        for name, arch, mink, maxk, noex in KEXTS
    ]

    template["Kernel"]["Patch"] = patches or []

    template["Kernel"]["Quirks"].update({
        "AppleXcpmCfgLock": False,   # Intel-only; innecesario en AMD
        "CustomSMBIOSGuid": False,
        "DisableIoMapper": True,    # receta Otus9051 (EFI del 5300U que arranca)
        "DisableLinkeditJettison": True,
        "LapicKernelPanic": True,   # AMD: evita panic por LAPIC; la ref lo usa
        "PanicNoKextDump": True,
        "PowerTimeoutKernelPanic": True,
        "ProvideCurrentCpuInfo": True,  # AMD: MSR/CPUID correctos al kernel
        "SetApfsTrimTimeout": -1,
        "XhciPortLimit": False,
    })

    template["Kernel"]["Emulate"].update({
        "Cpuid1Data": CPUID1_DATA,
        "Cpuid1Mask": CPUID1_MASK,
        # False: usamos AMDRyzenCPUPowerManagement+SMCAMDProcessor (receta Otus9051,
        # el EFI del 5300U que arranca), no el dummy.
        "DummyPowerManagement": False,
    })

    template["Misc"]["Boot"].update({
        # False: las entradas de recovery/instalador son auxiliares; en True
        # quedan ocultas (solo visibles con ESPACIO). Necesario para ver macOS.
        "HideAuxiliary": False,
        "HibernateMode": "None",
        "LauncherOption": "Full",
        "PickerAttributes": 17,
        "PickerMode": "Builtin",
        "ShowPicker": True,
        # 0: muestra el picker y espera selección sin auto-arrancar (evita que
        # se vaya solo a Linux). Subir a 5 tras terminar la instalación.
        "Timeout": 0,
        "PollAppleHotKeys": False,
    })

    template["Misc"]["Debug"].update({
        "AppleDebug": True,
        "ApplePanic": True,
        "DisableWatchDog": True,
        "DisplayLevel": DISPLAY_ALL,
        "Target": LOG_SERIAL_FILE,
    })

    template["Misc"]["Security"].update({
        "AllowSetDefault": True,
        "BlacklistAppleUpdate": True,
        "DmgLoading": "Any",
        "ExposeSensitiveData": 6,
        "ScanPolicy": 0,
        "SecureBootModel": "Disabled",
        "Vault": "Optional",
    })

    nv_guid = "7C436110-AB2A-4BBB-A880-FE41995C9F82"
    template["NVRAM"]["Add"][nv_guid] = {
        "boot-args": BOOT_ARGS,
        "csr-active-config": CSR_ACTIVE,
        "prev-lang:kbd": "en-US:0",
        "run-efi-updater": "No",
    }
    template["NVRAM"]["Delete"][nv_guid] = ["boot-args", "csr-active-config"]
    template["NVRAM"]["LegacyOverwrite"] = True
    template["NVRAM"]["WriteFlash"] = True

    template["PlatformInfo"].update({
        "Automatic": True,
        "UpdateDataHub": True,
        "UpdateNVRAM": True,
        "UpdateSMBIOS": True,
        "UpdateSMBIOSMode": "Custom",
    })

    template["PlatformInfo"]["Generic"].update({
        "AdviseFeatures": True,
        "MaxBIOSVersion": True,
        "MLB": MLB,
        "ROM": rom,
        "SpoofVendor": True,
        "SystemProductName": SMBIOS_MODEL,
        "SystemSerialNumber": SERIAL,
        "SystemUUID": system_uuid,
        "ProcessorType": 0,
        "SystemMemoryStatus": "Auto",
    })

    template["PlatformInfo"]["SMBIOS"].update({
        "BIOSVersion": "2087.0.0.0.0",
        "BIOSReleaseDate": "11/06/2024",
        "BIOSVendor": "Apple Inc.",
        "BoardManufacturer": "Apple Inc.",
        "BoardProduct": BOARD_ID,
        "SystemManufacturer": "Apple Inc.",
        "SystemProductName": SMBIOS_MODEL,
        "SystemSerialNumber": SERIAL,
        "SystemUUID": system_uuid,
        "SystemVersion": "1.0",
        "ChassisManufacturer": "Apple Inc.",
        "ChassisType": 9,
        "ProcessorType": 1537,
    })

    template["PlatformInfo"]["PlatformNVRAM"].update({
        "BID": BOARD_ID,
        "MLB": MLB,
        "ROM": rom,
        "SystemSerialNumber": SERIAL,
        "SystemUUID": system_uuid,
    })

    template["PlatformInfo"]["DataHub"].update({
        "BoardProduct": BOARD_ID,
        "SystemProductName": SMBIOS_MODEL,
        "SystemSerialNumber": SERIAL,
        "SystemUUID": system_uuid,
    })

    template["UEFI"]["Quirks"].update({
        "IgnoreInvalidFlexRatio": False,  # quirk Intel; no aplica a AMD
        "ForgeUefiSupport": False,        # firmware moderno: no forzar UEFI 2.x
        "ReleaseUsbOwnership": True,      # receta Otus9051 (5300U que arranca)
        "RequestBootVarRouting": True,
        "ResizeGpuBars": -1,
        "DisableSecurityPolicy": False,   # innecesario; el EFI de referencia=False
        "EnableVectorAcceleration": True, # acelera cripto UEFI (ref lo usa)
        "UnblockFsConnect": True,         # HP: desbloquea conexión de FS
    })

    template["UEFI"]["Drivers"] = [
        {
            "Path": "OpenRuntime.efi",
            "Enabled": True,
            "Comment": "OpenCore Runtime",
            "Arguments": "",
            "LoadEarly": False,
        },
        {
            # Driver HFS+ (binario de Apple): necesario para leer el volumen
            # HFS+ del BaseSystem.dmg del recovery/instalador. Sin el, OpenCore
            # monta el DMG pero no puede leer boot.efi y rebota al picker.
            "Path": "HfsPlus.efi",
            "Enabled": True,
            "Comment": "HFS+ (recovery/instalador)",
            "Arguments": "",
            "LoadEarly": False,
        },
    ]

    # Necesario al cargar drivers de sistema de archivos (HfsPlus.efi): conecta
    # los drivers a los volumenes tras cargarlos. ocvalidate lo exige.
    template["UEFI"]["ConnectDrivers"] = True

    template["UEFI"]["APFS"].update({
        "EnableJumpstart": True,
        "GlobalConnect": True,
        "HideVerbose": False,
    })

    template["UEFI"]["Audio"].update({
        "AudioSupport": False,
        "PlayChime": "Disabled",
    })

    template["UEFI"]["Output"].update({
        "InitialMode": "Auto",
        "ProvideConsoleGop": True,
        "ReconnectOnResChange": True,
    })

    template["UEFI"]["Input"]["KeySupport"] = True

    backup = EFI_OC / f"config_backup_{uuid.uuid4().hex[:8]}.plist"
    shutil.copy2(TEMPLATE_PATH, backup)
    print(f"  Backup: {backup}")

    output = EFI_OC / "config.plist"
    output.write_text(plistlib.dumps(template).decode())
    print(f"  Written: {output}")

    print()
    print("=" * 60)
    print("  CONFIG GENERATION COMPLETE")
    print("=" * 60)
    print(f"  SMBIOS:      {SMBIOS_MODEL}")
    print(f"  Serial:      {SERIAL}")
    print(f"  MLB:         {MLB}")
    print(f"  UUID:        {system_uuid}")
    print(f"  ROM:         {rom_str}")
    print(f"  Patches:     {len(patches)}")
    print(f"  Kexts:       {len(KEXTS)}")
    print(f"  Boot args:   {BOOT_ARGS}")
    print(f"  -NRedDPDelay: {USE_NRED_DP_DELAY}")
    print(f"  ACPI minimal test: {USE_MINIMAL_ACPI_FOR_FB_TEST}")
    print()
    print("  NEXT:")
    print("    Copy EFI/ to USB and boot.")
    print(f"    ocvalidate at: {TOOLS}/OpenCorePkg/Utilities/ocvalidate/")
    print("  NootedRed va ACTIVADO desde la instalación (Renoir no tiene")
    print("    framebuffer básico; sin él la pantalla queda negra).")
    return 0


if __name__ == "__main__":
    sys.exit(build_config())
