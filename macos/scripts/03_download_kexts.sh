#!/usr/bin/env bash
set -uo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
LOG_FILE="./03_download_kexts.log"

log()  { echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[!]${NC} $*" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}[✗]${NC} $*" | tee -a "$LOG_FILE"; }

cd "$(dirname "$0")/.." || exit 1
> "$LOG_FILE"

echo "===============================" | tee -a "$LOG_FILE"
echo " Descarga de Kexts Esenciales" | tee -a "$LOG_FILE"
echo " Fecha: $(date)" | tee -a "$LOG_FILE"
echo "===============================" | tee -a "$LOG_FILE"

KEXTS_DIR="./kexts"
mkdir -p "$KEXTS_DIR"

github_latest_asset() {
    local repo=$1 name=$2
    local api_url="https://api.github.com/repos/$repo/releases/latest"
    local json

    json=$(curl -sL "$api_url" 2>/dev/null) || { echo ""; return; }

    echo "$json" \
        | grep -o '"browser_download_url": *"[^"]*"' 2>/dev/null \
        | grep "$name" 2>/dev/null \
        | grep -i "RELEASE" 2>/dev/null \
        | grep -v -i "DEBUG" 2>/dev/null \
        | head -1 \
        | sed 's/.*"browser_download_url": *"\([^"]*\)".*/\1/' 2>/dev/null \
        || true
}

download_and_extract() {
    local name=$1 url=$2
    local zip_file="$KEXTS_DIR/${name}.zip"
    local dest_dir="$KEXTS_DIR/${name}"
    local http_code file_size

    log "Descargando $name..."
    http_code=$(curl -sL -w '%{http_code}' -o "$zip_file" "$url" 2>/dev/null) || { rm -f "$zip_file"; return 1; }

    if [ "$http_code" != "200" ]; then
        warn "  → HTTP $http_code para $name"
        rm -f "$zip_file"
        return 1
    fi

    file_size=$(stat -c%s "$zip_file" 2>/dev/null || echo 0)
    if [ "$file_size" -lt 1024 ]; then
        warn "  → Archivo demasiado pequeno (${file_size} bytes) para $name"
        cat "$zip_file" 2>/dev/null | tee -a "$LOG_FILE" || true
        rm -f "$zip_file"
        return 1
    fi

    mkdir -p "$dest_dir"
    if unzip -o "$zip_file" -d "$dest_dir" >> "$LOG_FILE" 2>&1; then
        rm -f "$zip_file"
        log "  → $name extraido en $dest_dir"
        return 0
    else
        warn "  → No se pudo extraer $zip_file"
        return 1
    fi
}

declare -A KEXTS=(
    ["Lilu"]="acidanthera/Lilu,Lilu"
    ["VirtualSMC"]="acidanthera/VirtualSMC,VirtualSMC"
    ["NootedRed"]="ChefKissInc/NootedRed,NootedRed"
    ["AppleALC"]="acidanthera/AppleALC,AppleALC"
    ["USBToolBox"]="USBToolBox/kext,USBToolBox"
    ["VoodooPS2"]="acidanthera/VoodooPS2,VoodooPS2Controller"
    ["NVMeFix"]="acidanthera/NVMeFix,NVMeFix"
    ["BrightnessKeys"]="acidanthera/BrightnessKeys,BrightnessKeys"
    ["AMDTscSync"]="naveenkrdy/AmdTscSync,AmdTscSync"
    ["RestrictEvents"]="acidanthera/RestrictEvents,RestrictEvents"
)

count=0
total=${#KEXTS[@]}
log "Resolviendo URLs via API de GitHub ($total kexts)..."

for name in "${!KEXTS[@]}"; do
    repo="${KEXTS[$name]%%,*}"
    filter="${KEXTS[$name]##*,}"

    download_url=$(github_latest_asset "$repo" "$filter")

    if [ -z "$download_url" ]; then
        warn "No se encontro asset '$filter' en $repo — saltando $name"
        continue
    fi

    download_and_extract "$name" "$download_url" && ((count++)) || true
done

log "Descargados: $count de $total kexts."
echo ""
log "Kexts en ./kexts/:"
find "$KEXTS_DIR" -name "*.kext" -type d 2>/dev/null | while read -r kext; do
    echo "  -> $kext" | tee -a "$LOG_FILE"
done

echo ""
echo "Para OCAT: arrastra cada .kext a Kernel > Add"
echo "NootedRed.kext REEMPLAZA WhateverGreen.kext (NO usar ambas)."
echo ""
echo "Siguiente paso: ./04_generate_config.sh"
