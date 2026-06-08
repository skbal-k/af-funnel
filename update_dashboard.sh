#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  update_dashboard.sh
#  Corre los agentes de Tableau y sube los datos a la web.
#  Doble clic o: bash /Users/skbal/partner_agent/update_dashboard.sh
# ─────────────────────────────────────────────────────────────

set -e
DIR="/Users/skbal/partner_agent"
cd "$DIR"

PYTHON=$(which python3)
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   AF Implementation Funnel — Dashboard Update ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

run_agent() {
    local name=$1
    local script=$2
    echo -e "${YELLOW}▶ Actualizando $name...${NC}"
    if $PYTHON "$DIR/$script" 2>&1; then
        echo -e "${GREEN}✅ $name OK${NC}"
    else
        echo -e "${RED}❌ $name falló (Tableau session expirada?) — continuando con los demás...${NC}"
    fi
    echo ""
}

# ── Correr todos los agentes ──────────────────────────────────
run_agent "LACA (All)"      "tableau_agent.py"
run_agent "Brazil"          "brazil_agent.py"
run_agent "Mexico"          "mexico_agent.py"
run_agent "LATAM-Growth"    "growth_agent.py"
run_agent "LATAM-Emerging"  "emg_agent.py"

# ── Copiar archivos LACA Overview ────────────────────────────
echo -e "${YELLOW}▶ Copiando datos LACA Overview...${NC}"
LACA_SRC="/Users/skbal/claude/tableau_agent/outputs"
if [ -d "$LACA_SRC" ]; then
    [ -f "$LACA_SRC/raw_data.csv" ]        && cp "$LACA_SRC/raw_data.csv"        "$DIR/output/laca_raw_data.csv"
    [ -f "$LACA_SRC/scale_accounts.csv" ]  && cp "$LACA_SRC/scale_accounts.csv"  "$DIR/output/laca_scale_accounts.csv"
    [ -f "$LACA_SRC/latest.json" ]         && cp "$LACA_SRC/latest.json"         "$DIR/output/laca_latest.json"
    # Copiar la imagen del funnel más reciente
    LATEST_IMG=$(ls -t "$LACA_SRC"/af_funnel_*.png 2>/dev/null | head -1)
    [ -n "$LATEST_IMG" ] && cp "$LATEST_IMG" "$DIR/output/laca_funnel.png"
    echo -e "${GREEN}✅ LACA Overview OK${NC}"
else
    echo -e "${RED}❌ Carpeta tableau_agent no encontrada, saltando LACA Overview...${NC}"
fi
echo ""

# ── Subir datos a GitHub ──────────────────────────────────────
echo -e "${YELLOW}▶ Subiendo datos a GitHub...${NC}"

cd "$DIR"

# Limpiar lock files si quedaron de antes
rm -f .git/index.lock .git/HEAD.lock .git/refs/heads/main.lock 2>/dev/null || true

git add output/
git diff --cached --quiet && echo "Sin cambios nuevos en los datos." || {
    git commit -m "Update dashboard data $(date '+%Y-%m-%d %H:%M')"
    git push
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ Dashboard actualizado!                    ║${NC}"
    echo -e "${GREEN}║  La web se actualiza en ~30 segundos.         ║${NC}"
    echo -e "${GREEN}║  https://af-funnel-hgyf4sj2neg8brgkyxywtw    ║${NC}"
    echo -e "${GREEN}║                    .streamlit.app             ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
}

echo ""
echo "Presioná Enter para cerrar..."
read
