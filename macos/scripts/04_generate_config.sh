#!/usr/bin/env bash
# ============================================================
# 04_generate_config.sh — Guía interactiva para OCAT
# Generar config.plist para Ryzen 3 5300U + MacBookPro16,3
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

print_step() { echo -e "\n${BOLD}${CYAN}═══ $1 ═══${NC}"; }

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════╗"
echo "║   CONFIGURACIÓN OCAT — Ryzen 3 5300U EFI    ║"
echo "║   SMBIOS: MacBookPro16,3                    ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Verificar que OCAT esté instalado ──────────────────────────
if ! command -v ocat &>/dev/null; then
    echo "❌ OCAT no está instalado. Ejecuta primero: ./01_install_ocat.sh"
    exit 1
fi

# ── Paso 1: Abrir OCAT ─────────────────────────────────────────
print_step "PASO 1 — Abrir OC Auxiliary Tools"
echo "Ejecutando: ocat"
echo ""
echo "Si no abre, ejecuta manualmente en otra terminal y presiona Enter."
echo ""
read -rp "Presiona Enter para continuar... "

ocat &
OCAT_PID=$!
sleep 2

# ── Paso 2: Actualizar OpenCore ───────────────────────────────
print_step "PASO 2 — Descargar OpenCore"
echo "En OCAT, ve a: Edit → Upgrade OpenCore and Kexts"
echo "Haz clic en 'Get OpenCore' para descargar la última versión."
echo ""
read -rp "¿Descargaste OpenCore? Presiona Enter para continuar... "

# ── Paso 3: Nuevo config.plist ─────────────────────────────────
print_step "PASO 3 — Nuevo config.plist"
echo "En OCAT, ve a: File → New"
echo "Esto crea un config.plist limpio con la estructura correcta."
echo ""
read -rp "¿Creaste el nuevo archivo? Presiona Enter... "

# ── Paso 4: Parches AMD ────────────────────────────────────────
print_step "PASO 4 — Aplicar parches AMD Zen 2"
echo "En OCAT:"
echo "  1. Ve a la pestaña 'Kernel' (barra lateral izquierda)"
echo "  2. Subpestaña 'Patch'"
echo "  3. En la esquina superior derecha, busca el menú desplegable"
echo "     de presets (ícono de estrellas/varita mágica)"
echo "  4. Selecciona: AMD Zen 2 (17h/Matisse/Renoir)"
echo ""
echo "  ⚠️  IMPORTANTE: Localiza el parche 'core_count'"
echo "     Cambia el valor 'Replace' por el hexadecimal"
echo "     correspondiente a tus 4 núcleos físicos: 04"
echo ""
echo "     Núcleos → Hex:"
echo "       4 cores → 04"
echo "       6 cores → 06"
echo "       8 cores → 08"
echo "      12 cores → 0C"
echo "      16 cores → 10"
echo ""
read -rp "¿Aplicaste los parches? Presiona Enter... "

# ── Paso 5: Configurar SMBIOS ──────────────────────────────────
print_step "PASO 5 — Configurar SMBIOS (MacBookPro16,3)"
echo "En OCAT:"
echo "  1. Ve a 'PI' (Platform Info) en la barra lateral"
echo "  2. Pestaña 'Generic'"
echo "  3. En 'SystemProductName' (o el dropdown de modelos):"
echo "     Escribe/selecciona: MacBookPro16,3"
echo "  4. Haz clic en el botón 'Generate' (flechas circulares)"
echo ""
echo "  Esto generará:"
echo "    • Serial Number (válido para Apple)"
echo "    • MLB (Board Serial)"
echo "    • UUID del sistema"
echo "    • ROM (dirección MAC)"
echo ""
read -rp "¿Configuraste el SMBIOS? Presiona Enter... "

# ── Paso 6: Agregar Kexts ─────────────────────────────────────
print_step "PASO 6 — Agregar Kexts"
echo "En OCAT, ve a: Kernel → Add"
echo ""
echo "Arrastra los siguientes .kext desde ./kexts/ a la lista de OCAT."
echo "OCAT los copiará a EFI/OC/Kexts/ y los ordenará automáticamente."
echo ""
echo "  📦 Kexts OBLIGATORIOS (cárgalos en este orden):"
echo ""
echo "  1. Lilu.kext              ← Base para todos los demás"
echo "  2. VirtualSMC.kext         ← Emula el SMC de Apple"
echo "  3. NootedRed.kext          ← Gráficos AMD (NO WhateverGreen!)"
echo "  4. AppleALC.kext           ← Audio"
echo "  5. USBToolBox.kext         ← USB"
echo "  6. VoodooPS2Controller.kext ← Teclado + Trackpad"
echo "  7. SMCBatteryManager.kext  ← Batería"
echo "  8. NVMeFix.kext            ← NVMe"
echo "  9. BrightnessKeys.kext     ← Brillo de pantalla"
echo "  10. AMDTscSync.kext        ← Sincronización TSC AMD"
echo "  11. RestrictEvents.kext    ← Bloquea procesos no deseados"
echo ""
echo "  ⚠️  NO agregues WhateverGreen.kext — NootedRed la reemplaza."
echo "  ⚠️  NO agregues AirportItlwm — tu chip RTL8822CE no es Intel."
echo ""
read -rp "¿Agregaste todos los kexts? Presiona Enter... "

# ── Paso 7: Drivers UEFI ───────────────────────────────────────
print_step "PASO 7 — Drivers UEFI"
echo "En OCAT, ve a: UEFI → Drivers"
echo "Asegúrate de tener estos drivers habilitados:"
echo ""
echo "  ✅ OpenRuntime.efi         ← Imprescindible"
echo "  ✅ OpenHfsPlus.efi         ← Lectura HFS+"
echo "  ✅ OpenCanopy.efi          ← GUI del picker (opcional)"
echo "  ✅ ResetNvramEntry.efi     ← Reset NVRAM"
echo "  ✅ ToggleSipEntry.efi      ← Desactivar SIP"
echo ""
read -rp "¿Verificaste los drivers? Presiona Enter... "

# ── Paso 8: ACPI ───────────────────────────────────────────────
print_step "PASO 8 — ACPI"
echo "En OCAT, ve a: ACPI → Add"
echo "Para Ryzen 3 5300U (laptop), los SSDTs recomendados:"
echo ""
echo "  ✅ SSDT-EC.aml       ← Embedded Controller (laptop)"
echo "  ✅ SSDT-PLUG.aml     ← Power management AMD"
echo "  ✅ SSDT-USBX.aml     ← USB power"
echo "  ✅ SSDT-PNLF.aml     ← Brightness control (laptop)"
echo "  ✅ SSDT-XOSI.aml     ← OS recognition"
echo ""
echo "Puedes generarlos con SSDTTime o usar los precompilados"
echo "disponibles en: https://github.com/dortania/Getting-Started-With-ACPI"
echo ""
read -rp "¿Agregaste los SSDTs? Presiona Enter... "

# ── Paso 9: Boot-args ──────────────────────────────────────────
print_step "PASO 9 — Boot Arguments (NVRAM)"
echo "En OCAT, ve a: NVRAM → Add → 7C436110-AB2A-4BBB-A880-FE41995C9F82"
echo ""
echo "Agrega/clona la key: boot-args"
echo "Valor recomendado para AMD:"
echo ""
echo "  -v keepsyms=1 debug=0x100 alcid=1 npci=0x2000"
echo ""
echo "  Explicación:"
echo "  -v            → Verbose mode (ver logs de arranque)"
echo "  keepsyms=1    → Muestra símbolos en kernel panic"
echo "  debug=0x100   → No reinicia automático en panic"
echo "  alcid=1       → Layout ID de audio (prueba 1, 3, 11, 13 si falla)"
echo "  npci=0x2000   → Fix PCI para algunas placas AMD"
echo ""
read -rp "¿Configuraste boot-args? Presiona Enter... "

# ── Paso 10: Guardar ───────────────────────────────────────────
print_step "PASO 10 — Guardar EFI"
echo "En OCAT: File → Save As"
echo ""
echo "Guarda el config.plist en: $(pwd)/EFI/OC/"
echo "OCAT copiará automáticamente todos los archivos necesarios a la estructura EFI."
echo ""
echo "La estructura final debe verse así:"
echo ""
echo "  EFI/"
echo "  ├── BOOT/"
echo "  │   └── BOOTx64.efi"
echo "  └── OC/"
echo "      ├── config.plist"
echo "      ├── ACPI/"
echo "      ├── Drivers/"
echo "      ├── Kexts/"
echo "      ├── Resources/"
echo "      └── Tools/"
echo ""
read -rp "¿Guardaste el config.plist? Presiona Enter... "

# ── Resumen final ──────────────────────────────────────────────
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅  CONFIGURACIÓN COMPLETADA          ${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo "Tu EFI está en: $(pwd)/EFI/"
echo ""
echo "Recuerda:"
echo "  1. Copiar 'com.apple.recovery.boot' a la raíz del USB (FAT32)"
echo "  2. Copiar la carpeta 'EFI' a la partición EFI del USB"
echo "  3. Ajustar BIOS/UEFI:"
echo "     - Disable Secure Boot"
echo "     - Disable Fast Boot"
echo "     - Enable Above 4G Decoding"
echo "     - Set UEFI boot mode"
echo "     - Disable CSM"
echo ""
echo "⚠️  WiFi: Tu chip RTL8822CE (10ec:c822) NO tiene soporte en macOS."
echo "    Opciones: Dongle USB WiFi compatible, o reemplazar tarjeta interna."
echo ""
read -rp "Presiona Enter para finalizar..."
