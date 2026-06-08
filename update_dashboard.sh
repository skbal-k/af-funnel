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
