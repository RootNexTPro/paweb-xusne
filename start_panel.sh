#!/usr/bin/env bash
# Start Nexus V2Ray / VLESS Panel
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

PORT="${PANEL_PORT:-8888}"
LOG_FILE="$DIR/panel.log"
PID_FILE="$DIR/panel.pid"

# Détection de Python (venv ou système)
if [ -f "$DIR/venv/bin/python3" ]; then
    PYTHON_BIN="$DIR/venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "❌ Erreur: python3 est introuvable."
    exit 1
fi

# Arrêt de l'ancienne instance si présente
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "[*] Arrêt de l'ancienne instance (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

# Libération du port
if command -v fuser >/dev/null 2>&1; then
    fuser -k "${PORT}/tcp" 2>/dev/null || true
fi

echo "[*] Démarrage du Nexus VLESS Web Panel sur le port $PORT..."
nohup "$PYTHON_BIN" "$DIR/app.py" >> "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"

sleep 2

if ps -p "$PID" > /dev/null 2>&1; then
    SERVER_IP=$(curl -s -m 3 https://api.ipify.org 2>/dev/null || curl -s -m 3 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    [ -z "$SERVER_IP" ] && SERVER_IP="127.0.0.1"

    echo "============================================================"
    echo "✅ Nexus Panel démarré avec succès ! (PID: $PID)"
    echo "🌐 URL locale  : http://127.0.0.1:$PORT"
    echo "🌍 URL publique: http://${SERVER_IP}:$PORT"
    echo "📄 Fichier log : $LOG_FILE"
    echo "============================================================"
else
    echo "❌ Erreur au démarrage du panel. Vérifiez les logs :"
    tail -n 20 "$LOG_FILE"
    exit 1
fi
