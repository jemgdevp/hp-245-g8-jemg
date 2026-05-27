#!/usr/bin/env python3
"""
OpenCore config.plist generator for AMD Ryzen 3 5300U (Renoir, Zen 2).
Target: macOS Sonoma, SMBIOS MacBookPro16,3.
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

SERIAL = "C02C40UNP3XY"
MLB = "C02003500GU0000JC"
SMBIOS_MODEL = "MacBookPro16,3"

# Núcleos físicos del Ryzen 3 5300U (4C/8T). Se inyecta en los patches
# AMD_Vanilla "cpuid_cores_per_package to constant"; dejarlo en 0 cuelga
# el arranque SMP/PCI.
PHYSICAL_CORES = 4

KEXTS = [
    ("Lilu",        "x86_64", "",      "",      False),
    ("VirtualSMC",  "x86_64", "",      "",      False),
    ("SMCBatteryManager", "x86_64", "", "",    False),
    ("SMCProcessor",   "x86_64", "",    "",     False),
    ("SMCSuperIO",     "x86_64", "",    "",     False),
    ("SMCLightSensor", "x86_64", "",    "",     False),
    ("SMCDellSensors", "x86_64", "",    "",     False),
    ("NootedRed",      "x86_64", "",    "",     False),
    ("AppleALC",       "x86_64", "",    "",     False),
    ("AppleALCU",      "x86_64", "23.0.0", "", False),
    ("USBToolBox",     "x86_64", "",    "",     False),
    ("UTBDefault",     "Any",    "",    "",     True),
    ("VoodooPS2Controller", "x86_64", "", "",   False),
    ("NVMeFix",        "x86_64", "",    "",     False),
    ("BrightnessKeys", "x86_64", "",    "",     False),
    ("AmdTscSync",     "x86_64", "",    "",     False),
    ("RestrictEvents", "x86_64", "",    "",     False),
]

BOOT_ARGS = "-v debug=0x100 keepsyms=1 alcid=1 revpatch=sbvmm"
CPUID1_DATA = bytes.fromhex("EA060900000000000000000000000000")
CPUID1_MASK = bytes.fromhex("FFFFFFFF000000000000000000000000")
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

    template["Booter"]["Quirks"].update({
        "AvoidRuntimeDefrag": True,
        "DevirtualiseMmio": True,
        "EnableSafeModeSlide": True,
        "ProvideCustomSlide": True,
        "SetupVirtualMap": True,
        "SyncRuntimePermissions": True,
        "RebuildAppleMemoryMap": True,
        "ResizeAppleGpuBars": 0,
    })

    template["Kernel"]["Add"] = [
        kext_entry(name, arch, mink, maxk, noex)
        for name, arch, mink, maxk, noex in KEXTS
    ]

    template["Kernel"]["Patch"] = patches or []

    template["Kernel"]["Quirks"].update({
        "AppleXcpmCfgLock": True,
        "CustomSMBIOSGuid": True,
        "DisableIoMapper": True,
        "DisableLinkeditJettison": True,
        "PanicNoKextDump": True,
        "PowerTimeoutKernelPanic": True,
        "ProvideCurrentCpuInfo": True,
        "SetApfsTrimTimeout": 999,
        "XhciPortLimit": False,
    })

    template["Kernel"]["Emulate"].update({
        "Cpuid1Data": CPUID1_DATA,
        "Cpuid1Mask": CPUID1_MASK,
        "DummyPowerManagement": True,
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
        "PollAppleHotKeys": True,
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
        "BoardProduct": "Mac-E7203C0F68AA0004",
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
        "BID": "Mac-E7203C0F68AA0004",
        "MLB": MLB,
        "ROM": rom,
        "SystemSerialNumber": SERIAL,
        "SystemUUID": system_uuid,
    })

    template["PlatformInfo"]["DataHub"].update({
        "BoardProduct": "Mac-E7203C0F68AA0004",
        "SystemProductName": SMBIOS_MODEL,
        "SystemSerialNumber": SERIAL,
        "SystemUUID": system_uuid,
    })

    template["UEFI"]["Quirks"].update({
        "IgnoreInvalidFlexRatio": True,
        "ReleaseUsbOwnership": True,
        "RequestBootVarRouting": True,
        "ResizeGpuBars": -1,
        "DisableSecurityPolicy": True,
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
    print()
    print("  NEXT:")
    print("    Copy EFI/ to USB and boot.")
    print(f"    ocvalidate at: {TOOLS}/OpenCorePkg/Utilities/ocvalidate/")
    return 0


if __name__ == "__main__":
    sys.exit(build_config())
