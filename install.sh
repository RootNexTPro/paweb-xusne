#!/usr/bin/env bash
# ==============================================================================
# Nexus Tunnel Web Panel - Script d'installation automatique VPS
# GitHub: https://github.com/RootNexTPro/paweb-xusne
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "============================================================"
echo "    🚀 Installation du Nexus Tunnel Control Panel v3.0     "
echo "============================================================"
echo -e "${NC}"

# 1. Vérification des privilèges Root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[❌] Ce script doit être exécuté avec les droits root (sudo).${NC}"
    exit 1
fi

INSTALL_DIR="/opt/paweb-xusne"
REPO_URL="https://github.com/RootNexTPro/paweb-xusne.git"
PANEL_PORT="${PANEL_PORT:-8888}"

# Détection de l'emplacement d'exécution
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
if [ -f "$CURRENT_DIR/app.py" ]; then
    INSTALL_DIR="$CURRENT_DIR"
    echo -e "${GREEN}[✔] Installation locale détectée dans : $INSTALL_DIR${NC}"
else
    echo -e "${YELLOW}[*] Téléchargement depuis GitHub vers $INSTALL_DIR...${NC}"
    apt-get update -y >/dev/null 2>&1 || true
    apt-get install -y git curl >/dev/null 2>&1
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}[*] Mise à jour du dossier existant...${NC}"
        cd "$INSTALL_DIR"
        git pull || true
    else
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
fi

cd "$INSTALL_DIR"

# 2. Mise à jour des paquets système et dépendances
echo -e "${YELLOW}[*] Installation des paquets système requis...${NC}"
apt-get update -y
apt-get install -y python3 python3-pip python3-venv curl psmisc git

# 3. Création et configuration du Virtualenv
echo -e "${YELLOW}[*] Configuration de l'environnement virtuel Python (venv)...${NC}"
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
fi

"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    echo -e "${YELLOW}[*] Installation des dépendances Python...${NC}"
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
else
    "$INSTALL_DIR/venv/bin/pip" install fastapi "uvicorn[standard]" pydantic "qrcode[pil]" pillow
fi

# Rendre exécutables les scripts bash
chmod +x "$INSTALL_DIR"/*.sh 2>/dev/null || true

# 4. Configuration du service systemd
echo -e "${YELLOW}[*] Création du service systemd 'nexus-panel'...${NC}"
cat <<EOF > /etc/systemd/system/nexus-panel.service
[Unit]
Description=Nexus Tunnel VLESS & V2Ray Control Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment=PANEL_PORT=$PANEL_PORT
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/app.py
Restart=always
RestartSec=5
StandardOutput=append:$INSTALL_DIR/panel.log
StandardError=append:$INSTALL_DIR/panel.log

[Install]
WantedBy=multi-user.target
EOF

# 5. Gestion Pare-feu (UFW)
if command -v ufw >/dev/null 2>&1; then
    if ufw status | grep -q "Status: active"; then
        echo -e "${YELLOW}[*] Ouverture du port $PANEL_PORT sur le pare-feu UFW...${NC}"
        ufw allow "$PANEL_PORT"/tcp comment "Nexus Web Panel" || true
    fi
fi

# 6. Activation et démarrage du service
echo -e "${YELLOW}[*] Démarrage du service...${NC}"
systemctl daemon-reload
systemctl enable nexus-panel
systemctl restart nexus-panel

# 7. Vérification de bon fonctionnement
sleep 3
SERVER_IP=$(curl -s -m 3 https://api.ipify.org 2>/dev/null || curl -s -m 3 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
[ -z "$SERVER_IP" ] && SERVER_IP="VOTRE_IP_VPS"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:"$PANEL_PORT"/api/health || echo "FAIL")

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}   🎉 Félicitations ! Nexus Web Panel est installé !      ${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "${CYAN}🌐 Accès au Web Panel :${NC} http://${SERVER_IP}:${PANEL_PORT}"
echo -e "${CYAN}👤 SuperAdmin login   :${NC} superadmin"
echo -e "${CYAN}🔑 Mot de passe       :${NC} nexus2026!"
echo ""
echo -e "${CYAN}🏪 Compte Revendeur   :${NC} revendeur_douala"
echo -e "${CYAN}🔑 Mot de passe       :${NC} reseller123"
echo "------------------------------------------------------------"
echo -e "${YELLOW}Commandes utiles :${NC}"
echo "  • Statut du service   : systemctl status nexus-panel"
echo "  • Voir les logs       : journalctl -u nexus-panel -f"
echo "  • Redémarrer le panel : systemctl restart nexus-panel"
echo "  • Arrêter le panel    : systemctl stop nexus-panel"
echo -e "${GREEN}============================================================${NC}"
