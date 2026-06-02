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
import argparse
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

# Identidad FIJA del SMBIOS. Antes se regeneraban SystemUUID y ROM en CADA ejecución
# (uuid4 + ROM aleatorio), lo que rompía la identidad de la "Mac" entre perfiles/regens
# (iMessage/iCloud, NVRAM). Se fijan a los valores del config.plist que ya funciona en el
# disco para que los 3 perfiles compartan identidad y no cambie en cada generación.
SYSTEM_UUID = "7DE77C0C-70C3-4EC0-9457-E2753A502021"
ROM_FIXED = bytes.fromhex("64cbd3b317f3")

# Núcleos físicos del Ryzen 3 5300U (4C/8T). Se inyecta en los patches
# AMD_Vanilla "cpuid_cores_per_package to constant"; dejarlo en 0 cuelga
# el arranque SMP/PCI.
PHYSICAL_CORES = 4

# Formato: (bundle_path, arch, minkernel, maxkernel, noexec)
# Para sub-plugins: bundle_path = "Parent.kext/Contents/PlugIns/PluginName"
# (sin la extensión final; kext_entry la añade automáticamente)
# OpenCore NO inyecta PlugIns automáticamente: cada sub-plugin debe declararse.
# Orden crítico: plugins ANTES que el bundle padre que los registra.
KEXTS = [
    ("Lilu",        "x86_64", "",      "",      False),
    # Codeless: evita panics de AppleMCEReporter en AMD ≥ macOS 12.3
    ("AppleMCEReporterDisabler", "x86_64", "", "", True),
    ("VirtualSMC",  "x86_64", "",      "",      False),
    # ForgedInvariant: TSC-sync de ChefKiss (reemplaza AmdTscSync).
    ("ForgedInvariant", "x86_64", "",  "",      False),
    # AMD PM kexts — OFF hasta instalar (kernel panic con v0.7.2 + esta config)
    ("SMCAMDProcessor", "x86_64", "", "", False),
    ("AMDRyzenCPUPowerManagement", "x86_64", "", "", False),
    ("SMCBatteryManager", "x86_64", "", "",    False),
    ("SMCSuperIO",     "x86_64", "",    "",     False),
    ("SMCLightSensor", "x86_64", "",    "",     False),
    # NootedRed ON desde la instalación (Renoir/Lucienne no tiene framebuffer básico sin él)
    ("NootedRed",      "x86_64", "",    "",     False),
    ("AppleALC",       "x86_64", "",    "",     False),
    ("AppleALCU",      "x86_64", "23.0.0", "", False),
    ("USBToolBox",     "x86_64", "",    "",     False),
    ("UTBDefault",     "Any",    "",    "",     True),
    # ── Input: PS/2 teclado ──────────────────────────────────────────────────
    # VoodooPS2Controller bundle raíz (gestiona el nub i8042)
    ("VoodooPS2Controller", "x86_64", "", "",   False),
    # Sub-plugins PS2 (deben declararse explícitamente; OpenCore no los inyecta solo)
    # VoodooInput del PS2 desactivado: solo debe haber una instancia de VoodooInput
    # activa. La del I2C es la que gestiona el touchpad; la del PS2 es redundante
    # y causa corrupción de eventos si ambas cargan.
    ("VoodooPS2Controller.kext/Contents/PlugIns/VoodooInput",    "x86_64", "", "", False),  # → Enabled=False
    ("VoodooPS2Controller.kext/Contents/PlugIns/VoodooPS2Keyboard",  "x86_64", "", "", False),
    ("VoodooPS2Controller.kext/Contents/PlugIns/VoodooPS2Mouse",     "x86_64", "", "", False),
    ("VoodooPS2Controller.kext/Contents/PlugIns/VoodooPS2Trackpad",  "x86_64", "", "", False),
    # ── Input: touchpad I2C (ELAN0708 en bus AMDI0010/I2CD) ─────────────────
    # Plugins de VoodooI2C ANTES del bundle principal (requisito de carga de OpenCore)
    ("VoodooI2C.kext/Contents/PlugIns/VoodooGPIO",        "x86_64", "", "", False),
    ("VoodooI2C.kext/Contents/PlugIns/VoodooI2CServices", "x86_64", "", "", False),
    ("VoodooI2C.kext/Contents/PlugIns/VoodooInput",       "x86_64", "", "", False),
    # Bundle principal VoodooI2C + satélite HID
    ("VoodooI2C",      "x86_64", "",    "",     False),
    ("VoodooI2CHID",   "x86_64", "",    "",     False),
    # ── Resto ────────────────────────────────────────────────────────────────
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
# True → -NRedNoAccel: framebuffer-only sin Metal (aisla si el cuelgue está en
# la aceleración gráfica vs el panel eDP). Prueba #3 según diagnóstico sess.11.
# -NRedNoAccel: probado, NO resolvió el freeze de la fase final. Ni Otus9051 ni
# beitanam (Lenovo V15, mismo CPU, funcionales) lo usan. Apagado para no dejar el
# iGPU en estado a medias. -NRedDPDelay SÍ se mantiene (beitanam lo usa con panel eDP).
USE_NRED_NO_ACCEL = False
_NRED_EXTRA = " -NRedDPDelay" if USE_NRED_DP_DELAY else ""
_NRED_EXTRA += " -NRedNoAccel" if USE_NRED_NO_ACCEL else ""
# Polling forzado de VoodooI2C: boot-arg real es "-vi2c-force-polling".
# "voodooI2CPoling=1" NO existe en el binario de VoodooI2C v2.9.1 — era inefectivo.
# Con los plugins declarados correctamente, VoodooI2C cae automáticamente a polling
# si no encuentra interrupts GPIO válidas (el Otus9051 no usa este boot-arg y funciona).
USE_I2C_POLLING = False
_I2C_EXTRA = " -vi2c-force-polling" if USE_I2C_POLLING else ""
# revblock=media: arg de RestrictEvents (ya en KEXTS). Bloquea mediaanalysisd en
# Ventura+ con GPUs Metal-1 como la Vega 6/NootedRed — recomendado por ChefKiss para
# estabilidad/aspecto del iGPU. Inocuo si el problema real es el UMA Frame Buffer (BIOS).
# AMDBacklight=1: ACTIVA el slider de brillo. Confirmado en el código de NootedRed
# (Backlight.cpp:87-91): solo instala el backlight si modelType==Laptop, y Lilu marca
# Laptop SOLO si el SMBIOS contiene "Book". Con iMac20,1 (sin "Book") NootedRed lo trata
# como desktop y NO registra el backlight. AMDBacklight=1 fuerza el override sin cambiar
# de SMBIOS. (Alternativa probada en Otus9051: SMBIOS MacBookPro16,2, que activa el flag solo.)
# boot-args COMUNES a todos los perfiles (lo que hace funcionar el hardware):
#   npci=0x3000 alcid=13 agdpmod=pikera revblock=media AMDBacklight=1 -NRedDPDelay
# El prefijo de DEBUG (-v keepsyms=1 debug=0x100) solo va en install/stable.
_BASE_ARGS = "npci=0x3000 alcid=13 agdpmod=pikera revblock=media AMDBacklight=1" + _NRED_EXTRA + _I2C_EXTRA
_DEBUG_ARGS = "-v keepsyms=1 debug=0x100"
# BOOT_ARGS por defecto (perfil stable) — mantiene el comportamiento histórico.
BOOT_ARGS = _DEBUG_ARGS + " " + _BASE_ARGS

# ============================================================================
# PERFILES DE EFI — un solo árbol de kexts/SSDTs, 3 config.plist intercambiables.
#   install     : para el USB instalador (verbose+debug, USB provisional UTBDefault).
#   stable      : = el EFI que arranca HOY (ancla de seguridad anti-regresión).
#   postinstall : uso diario (sin verbose/debug, auto-arranque, ECEnabler + SSDT-RTCAWAC,
#                 SetApfsTrimTimeout=0 para HDD; AMD PM sigue OFF por incompatibilidad).
# Solo cambia lo listado aquí; todo lo demás (quirks, SMBIOS, parches AMD, input...)
# es INVARIANTE de hardware y vive una sola vez en build_config().
# ============================================================================
PROFILES = {
    "install": dict(
        verbose=True,  target=67, apple_debug=True,  watchdog=True,  timeout=0,
        apfs_trim=-1,  usb="utbdefault", extra_kexts=[], extra_ssdts=[],
    ),
    "stable": dict(
        verbose=True,  target=67, apple_debug=True,  watchdog=True,  timeout=0,
        apfs_trim=-1,  usb="utbdefault", extra_kexts=[], extra_ssdts=[],
    ),
    "postinstall": dict(
        verbose=False, target=3,  apple_debug=False, watchdog=False, timeout=5,
        apfs_trim=0,   usb="utbmap",
        extra_kexts=[("ECEnabler", "x86_64", "", "", False)],
        extra_ssdts=["SSDT-RTCAWAC"],
    ),
}

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


def kext_entry(bundle_path, arch, minkernel, maxkernel, noexec):
    # Soporta tanto kexts simples ("Lilu") como sub-plugins
    # ("VoodooI2C.kext/Contents/PlugIns/VoodooGPIO").
    # Para sub-plugins, el ejecutable es el último componente del path.
    if "/" in bundle_path:
        exec_name = bundle_path.split("/")[-1]
        full_bundle = f"{bundle_path}.kext"
    else:
        exec_name = bundle_path
        full_bundle = f"{bundle_path}.kext"

    entry = {
        "Arch": arch,
        "BundlePath": full_bundle,
        "Comment": exec_name,
        "Enabled": True,
        "MaxKernel": maxkernel,
        "MinKernel": minkernel,
        "PlistPath": "Contents/Info.plist",
    }
    if not noexec:
        entry["ExecutablePath"] = f"Contents/MacOS/{exec_name}"
    else:
        entry["ExecutablePath"] = ""
    return entry


def build_config(profile="stable"):
    cfg = PROFILES[profile]
    print("=" * 60)
    print(f"  OpenCore config.plist — AMD Renoir — perfil: {profile}")
    print("=" * 60)

    clone_amd_vanilla()
    patches = load_amd_patches()
    print(f"  Kernel patches loaded: {len(patches)}")

    template = plistlib.loads(TEMPLATE_PATH.read_bytes())
    system_uuid = SYSTEM_UUID   # FIJO (no regenerar; ver SYSTEM_UUID arriba)
    rom = ROM_FIXED             # FIJO
    rom_str = ":".join(f"{b:02x}" for b in rom)

    # boot-args del perfil: el prefijo de debug (-v keepsyms debug=0x100) solo en verbose.
    boot_args = (_DEBUG_ARGS + " " + _BASE_ARGS) if cfg["verbose"] else _BASE_ARGS

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
            "SSDT-ALS0", "SSDT-EC", "SSDT-PLUG-ALT", "SSDT-PNLF",
            "SSDT-USBX", "SSDT-XOSI",
        ]
        print("  [FB TEST] Usando set ACPI MINIMAL estilo Otus (menos colisiones)")
    else:
        # Set completo (tu versión actual, validada contra DSDT)
        ACPI_SSDTS = [
            "SSDT-ALS0", "SSDT-EC", "SSDT-GPRW", "SSDT-HPET", "SSDT-PLUG-ALT",
            "SSDT-PMC", "SSDT-PNLF", "SSDT-PS2K", "SSDT-USBX", "SSDT-XOSI", "SSDT-USB-Reset",
        ]

    # SSDTs extra del perfil (p.ej. SSDT-RTCAWAC en postinstall, para sleep/RTC).
    # Solo se añaden si el .aml existe en EFI/OC/ACPI/.
    for extra in cfg["extra_ssdts"]:
        if (EFI_OC / "ACPI" / f"{extra}.aml").exists() and extra not in ACPI_SSDTS:
            ACPI_SSDTS.append(extra)
        elif extra not in ACPI_SSDTS:
            print(f"  [AVISO] {extra}.aml no existe en ACPI/ — perfil {profile} lo omite")

    # SSDTs del HP 245 G8. SSDT-PLUG-ALT (no SSDT-PLUG): la versión Intel de PLUG
    # busca objetos P001, P002... que no existen en AMD (solo P000); causa
    # AE_NOT_FOUND en verbose. SSDT-PLUG-ALT define objetos virtuales CP00-CP0F
    # compatibles con AMD. Copiado de docs/hp-245-g8-efi-base y otus9051 (mismo CPU).
    # SSDT-EC: EC válido temprano en SBRG (crítico).
    # SSDT-GPRW + parche GPRW->XPRW: neutraliza instant-wake que cuelga bus PCI.
    # SSDT-USB-Reset: desactiva RHUB de XHC0/XHC1 para que macOS re-enumere USB.
    # Paths validados contra docs/DSDT.aml: \_SB.PCI0.GP17.XHC0.RHUB y XHC1.RHUB.
    template["ACPI"]["Add"] = [
        {"Comment": s, "Enabled": True, "Path": f"{s}.aml"} for s in ACPI_SSDTS
    ]
    # Parche GPRW→XPRW: neutraliza instant-wake (5 bytes, incluye arg count 0x02).
    # Parche _OSI→XOSI: requerido para que SSDT-XOSI funcione. Sin este rename,
    # el DSDT llama al _OSI real de Apple (que no conoce "Darwin" como Windows)
    # y el bus I2C AMDI0010 no se activa en macOS. El Otus9051 (5300U que arranca
    # con touchpad) tiene este parche; sin él SSDT-XOSI es letra muerta.
    template["ACPI"]["Patch"] = [
        {
            "Base": "", "BaseSkip": 0,
            "Comment": "change GPRW to XPRW",
            "Count": 0, "Enabled": True, "Limit": 0,
            "Find": bytes.fromhex("4750525702"), "Replace": bytes.fromhex("5850525702"),
            "Mask": b"", "ReplaceMask": b"",
            "OemTableId": b"", "Skip": 0,
            "TableLength": 0, "TableSignature": b"",
        },
        {
            "Base": "", "BaseSkip": 0,
            "Comment": "_OSI to XOSI rename (requiere SSDT-XOSI.aml)",
            "Count": 0, "Enabled": True, "Limit": 0,
            "Find": bytes.fromhex("5f4f5349"), "Replace": bytes.fromhex("584f5349"),
            "Mask": b"", "ReplaceMask": b"",
            "OemTableId": b"", "Skip": 0,
            "TableLength": 0, "TableSignature": b"",
        },
    ]

    # Esquema de memoria "moderno" (sesión 11): Otus9051 (Ryzen 3 5300U exacto
    # que arranca Ventura) usa este esquema. El legacy se fijó en sesión 2 porque
    # la EFI de referencia HP 245 G8 (5500U) lo usaba y el moderno colgaba tras
    # ExitBootServices — pero eso fue antes de alinear SMBIOS, power-kexts y
    # ACPI. Grok + issue #206 confirman que Otus9051 (idéntico CPU) usa moderno.
    # DevirtualiseMmio + ProtectUefiServices = False: ALINEADO con Otus9051
    # (config real del mismo CPU 5300U que arranca; verificado tiene ambos False).
    # En True el instalador se congela en su fase final (sellado APFS / I/O tardía):
    # un fault de mapeo MMIO bajo carga sostenida cuelga el kernel sin verbose.
    template["Booter"]["Quirks"].update({
        "AvoidRuntimeDefrag": True,
        "DevirtualiseMmio": False,
        "EnableSafeModeSlide": True,
        "EnableWriteUnprotector": False,
        "ProtectUefiServices": False,
        "ProvideCustomSlide": True,
        "RebuildAppleMemoryMap": True,
        "ResizeAppleGpuBars": -1,
        "SetupVirtualMap": True,
        "SyncRuntimePermissions": True,
    })

    # Lista de kexts efectiva según perfil.
    kexts = list(KEXTS)
    # Bloque USB: postinstall usa el mapa real UTBMap si existe; si no, mantiene
    # UTBDefault (provisional) y avisa. install/stable usan siempre UTBDefault.
    if cfg["usb"] == "utbmap":
        if (EFI_OC / "Kexts" / "UTBMap.kext").exists():
            kexts = [k for k in kexts if k[0] != "UTBDefault"]
            kexts.append(("UTBMap", "Any", "", "", True))
            print("  USB: UTBMap.kext (mapa real)")
        else:
            print("  [AVISO] perfil postinstall pide UTBMap.kext pero aún no existe;")
            print("          se mantiene UTBDefault. Genera el mapping real en macOS (USBMap).")
    # Kexts extra del perfil (p.ej. ECEnabler en postinstall)
    kexts += cfg["extra_kexts"]

    template["Kernel"]["Add"] = [
        kext_entry(name, arch, mink, maxk, noex)
        for name, arch, mink, maxk, noex in kexts
    ]

    template["Kernel"]["Patch"] = patches or []

    template["Kernel"]["Quirks"].update({
        "AppleXcpmCfgLock": False,   # Intel-only; innecesario en AMD
        "CustomSMBIOSGuid": False,
        "DisableIoMapper": False,   # Otus9051 REAL lo tiene False (el comentario
                                    # previo "True=receta Otus" era erróneo): VT-d/IOMMU
                                    # activo no estorba y el False alinea con la ref que arranca.
        "DisableLinkeditJettison": True,
        "LapicKernelPanic": False,  # Otus9051 lo tiene False; True añadía panic-paths
                                    # innecesarios. Alineado con la ref funcional.
        "PanicNoKextDump": True,
        "PowerTimeoutKernelPanic": True,
        "ProvideCurrentCpuInfo": True,  # AMD: MSR/CPUID correctos al kernel
        # SetApfsTrimTimeout: -1 (default ~10s) en install/stable; 0 en postinstall
        # porque macOS está en HDD mecánico (sin TRIM): evita penalizar el arranque
        # intentando un TRIM que no aplica.
        "SetApfsTrimTimeout": cfg["apfs_trim"],
        "XhciPortLimit": False,
    })

    template["Kernel"]["Emulate"].update({
        "Cpuid1Data": CPUID1_DATA,
        "Cpuid1Mask": CPUID1_MASK,
        # DummyPowerManagement=True en TODOS los perfiles. AMDRyzenCPUPowerManagement +
        # SMCAMDProcessor se quedan OFF (no re-activar): el panic no es de versión sino
        # estructural — esos kexts escriben P-states legacy por MSR y NO implementan CPPC,
        # que es justo lo que las APU Lucienne móviles usan para escalar; sin CPPC los
        # P-states cuelgan/paniquean (Caps Lock). El propio dev de NootedRed recomienda
        # quitarlos en APUs; el SMU del firmware ya gobierna frecuencia/voltaje. Para ver
        # temperaturas se puede usar SMCProcessorAMD (monitor, no toca PM) — opcional.
        "DummyPowerManagement": True,
    })

    # Kexts deshabilitados explícitamente:
    # - AMD PM: kernel panic (Caps Lock on) en esta config de instalación
    # - VoodooInput del PS2: duplicado — solo debe haber UNA instancia de VoodooInput
    #   activa. La del I2C gestiona el touchpad ELAN0708; si carga la del PS2 también,
    #   el IORegistry tiene dos motores multitouch y los eventos se corrompen.
    KEXTS_DISABLED = {
        "AMDRyzenCPUPowerManagement",
        "SMCAMDProcessor",
        "VoodooInput",  # el del PS2 (BundlePath contiene PlugIns de VoodooPS2Controller)
    }
    for entry in template["Kernel"]["Add"]:
        bp = entry.get("BundlePath", "")
        comment = entry.get("Comment", "")
        is_ps2_input = (comment == "VoodooInput" and "VoodooPS2Controller" in bp)
        is_amd_pm = comment in ("AMDRyzenCPUPowerManagement", "SMCAMDProcessor")
        if is_ps2_input or is_amd_pm:
            entry["Enabled"] = False

    template["Misc"]["Boot"].update({
        # False: las entradas de recovery/instalador son auxiliares; en True
        # quedan ocultas (solo visibles con ESPACIO). Necesario para ver macOS.
        "HideAuxiliary": False,
        "HibernateMode": "None",
        # Disabled: NO re-registrar la entrada de arranque "OpenCore" en NVRAM.
        # Con LauncherOption=Full, tras el mkfs.vfat quedaba una entrada NVRAM rancia
        # que provocaba el bucle "OCB: StartImage failed - Already Started" (re-entrada
        # del firmware en OpenCore). Como ya tenemos el Bootstrap correcto en
        # \EFI\BOOT\BOOTx64.efi, el firmware arranca por su ruta fallback sin necesitar
        # ninguna entrada NVRAM -> Disabled corta la re-registración de raíz.
        "LauncherOption": "Disabled",
        "PickerAttributes": 17,
        "PickerMode": "Builtin",
        "ShowPicker": True,
        # Timeout por perfil: 0 (install/stable) muestra el picker y espera selección
        # sin auto-arrancar (evita irse solo a Linux); 5 (postinstall) auto-arranca a macOS.
        "Timeout": cfg["timeout"],
        "PollAppleHotKeys": False,
    })

    # Misc>Debug por perfil: install/stable escriben logs en la ESP (Target=67) para
    # diagnóstico; postinstall usa Target=3 (sin opencore-*.txt en disco) + sin watchdog.
    # ApplePanic se deja True (barato y útil para post-mortem de kernel panics).
    template["Misc"]["Debug"].update({
        "AppleDebug": cfg["apple_debug"],
        "ApplePanic": True,
        "DisableWatchDog": cfg["watchdog"],
        "DisplayLevel": DISPLAY_ALL,
        "Target": cfg["target"],
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

    # Herramienta CleanNvram.efi visible en el picker (Auxiliary=False -> sin ESPACIO).
    # Necesaria para limpiar la entrada NVRAM rancia autorreferencial que causa el bucle
    # "OCB/BS: StartImage failed - Already Started" (OpenCore intentando arrancarse a sí
    # mismo desde una entrada de arranque vieja de cuando LauncherOption=Full). El binario
    # vive en EFI/OC/Tools/CleanNvram.efi (release oficial 1.0.7). Resetear NVRAM es seguro:
    # los boot-args se re-inyectan vía NVRAM>Add en cada arranque.
    template["Misc"]["Tools"] = [
        {
            "Arguments": "",
            "Auxiliary": False,
            "Comment": "Reset NVRAM (borra entradas rancias; fix Already Started)",
            "Enabled": True,
            "Flavour": "Auto",
            "FullNvramAccess": True,
            "Name": "Reset NVRAM (CleanNvram)",
            "Path": "CleanNvram.efi",
            "RealPath": False,
            "TextMode": False,
        },
    ]

    nv_guid = "7C436110-AB2A-4BBB-A880-FE41995C9F82"
    template["NVRAM"]["Add"][nv_guid] = {
        "boot-args": boot_args,
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

    plist_bytes = plistlib.dumps(template)

    # 1) Copia versionada del perfil en EFI/OC/profiles/config-<profile>.plist
    profiles_dir = EFI_OC / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    profile_out = profiles_dir / f"config-{profile}.plist"
    profile_out.write_bytes(plist_bytes)
    print(f"  Perfil:  {profile_out}")

    # 2) config.plist ACTIVO (el que sincroniza 06_sync_usb_efi.sh)
    output = EFI_OC / "config.plist"
    output.write_bytes(plist_bytes)
    print(f"  Activo:  {output}  (perfil {profile})")

    print()
    print("=" * 60)
    print("  CONFIG GENERATION COMPLETE")
    print("=" * 60)
    print(f"  SMBIOS:      {SMBIOS_MODEL}")
    print(f"  Serial:      {SERIAL}")
    print(f"  MLB:         {MLB}")
    print(f"  UUID:        {system_uuid}")
    print(f"  ROM:         {rom_str}")
    print(f"  Perfil:      {profile}")
    print(f"  Patches:     {len(patches)}")
    print(f"  Kexts:       {len(kexts)}")
    print(f"  SSDTs:       {len(ACPI_SSDTS)}")
    print(f"  Boot args:   {boot_args}")
    print(f"  Debug Target: {cfg['target']}  Timeout: {cfg['timeout']}  ApfsTrim: {cfg['apfs_trim']}")
    print()
    print("  NEXT:")
    if profile == "install":
        print("    Sincroniza al USB:  ./scripts/06_sync_usb_efi.sh")
    elif profile == "postinstall":
        print("    Copia EFI/OC/config.plist al ESP del disco interno (MountEFI) + Reset NVRAM.")
    else:
        print("    Sincroniza con ./scripts/06_sync_usb_efi.sh o copia al disco.")
    print(f"    ocvalidate: {TOOLS}/ocvalidate ./EFI/OC/config.plist")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera config.plist de OpenCore por perfil (install/stable/postinstall)."
    )
    parser.add_argument(
        "--profile", choices=list(PROFILES.keys()), default="stable",
        help="Perfil de EFI a generar (default: stable = el EFI que arranca hoy).",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Genera los 3 perfiles en EFI/OC/profiles/ y deja 'stable' como config.plist activo.",
    )
    args = parser.parse_args()
    if args.all:
        for p in ("install", "postinstall", "stable"):  # stable al final → queda activo
            build_config(p)
        sys.exit(0)
    sys.exit(build_config(args.profile))
