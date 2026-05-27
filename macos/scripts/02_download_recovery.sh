#!/usr/bin/env bash
# ============================================================
# 02_download_recovery.sh — Descargar macOS Sonoma Recovery
# Proyecto: EFI Hackintosh Ryzen 3 5300U (Renoir/Lucienne)
# Modelo:   Mac-937A206F2EE63C01 → macOS 14 Sonoma
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
LOG_FILE="./02_download_recovery.log"

log()  { echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[!]${NC} $*" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}[✗]${NC} $*" | tee -a "$LOG_FILE"; }

cd "$(dirname "$0")/.." || exit 1
PROJECT_ROOT="$(pwd)"
> "$LOG_FILE"

echo "===============================" | tee -a "$LOG_FILE"
echo " macOS Sonoma Recovery Download" | tee -a "$LOG_FILE"
echo " Fecha: $(date)" | tee -a "$LOG_FILE"
echo "===============================" | tee -a "$LOG_FILE"

# ── Paso 1: Clonar OpenCorePkg ─────────────────────────────────
if [ ! -d "tools/OpenCorePkg" ]; then
    log "Clonando repositorio OpenCorePkg..."
    git clone --depth 1 https://github.com/acidanthera/OpenCorePkg.git tools/OpenCorePkg
else
    log "OpenCorePkg ya clonado. Actualizando..."
    (cd tools/OpenCorePkg && git pull)
fi

# ── Paso 2: Ejecutar macrecovery ───────────────────────────────
RECOVERY_DIR="tools/OpenCorePkg/Utilities/macrecovery"
RECOVERY_FILE="$RECOVERY_DIR/macrecovery.py"

if [ ! -f "$RECOVERY_FILE" ]; then
    err "No se encontró $RECOVERY_FILE. ¿Falló el clonado?"
    exit 1
fi

log "Descargando macOS Sonoma (Mac-937A206F2EE63C01) desde servidores Apple..."
log "Esto puede tomar varios minutos dependiendo de tu conexión."

cd "$RECOVERY_DIR"

# Mac-937A206F2EE63C01 = macOS 14 Sonoma
python3 macrecovery.py \
    -b Mac-937A206F2EE63C01 \
    -m 00000000000000000 \
    download \
    2>&1 | tee -a "$LOG_FILE"

# ── Paso 3: Mover archivos a carpeta de proyecto ──────────────
PROJECT_RECOVERY="$PROJECT_ROOT/recovery"
mkdir -p "$PROJECT_RECOVERY"

if [ -f "com.apple.recovery.boot/BaseSystem.dmg" ]; then
    cp -r com.apple.recovery.boot "$PROJECT_RECOVERY/"
    log "Archivos de recuperacion copiados a: $PROJECT_RECOVERY/com.apple.recovery.boot/"
    log "Archivos obtenidos:"
    ls -lh "$PROJECT_RECOVERY/com.apple.recovery.boot/" | tee -a "$LOG_FILE"
else
    err "No se generó BaseSystem.dmg. Revisa $LOG_FILE"
    exit 1
fi

cd "$PROJECT_ROOT"

echo ""
log "Descarga completada. Estructura:"
echo "  recovery/com.apple.recovery.boot/"
echo "    BaseSystem.dmg"
echo "    BaseSystem.chunklist"
echo ""
log "Para USB Ventoy: copia 'com.apple.recovery.boot' a la raiz del USB."
echo ""
echo "Siguiente paso: ./03_download_kexts.sh"
