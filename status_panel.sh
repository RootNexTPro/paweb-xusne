#!/usr/bin/env bash
# Status Nexus Panel
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PORT="${PANEL_PORT:-8888}"
PID_FILE="$DIR/panel.pid"

SERVER_IP=$(curl -s -m 3 https://api.ipify.org 2>/dev/null || curl -s -m 3 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
[ -z "$SERVER_IP" ] && SERVER_IP="127.0.0.1"

echo "=== STATUT DU NEXUS VLESS PANEL ==="
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🟢 En cours d'exécution (PID: $PID)"
        echo "🌐 Port d'écoute : $PORT"
        echo "🌍 Accès externe : http://${SERVER_IP}:$PORT"
        
        # Test HTTP API Health
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:"$PORT"/api/health || echo "FAIL")
        if [ "$HTTP_CODE" = "200" ]; then
            echo "✅ Réponse API Health 200 OK :"
            curl -s http://127.0.0.1:"$PORT"/api/health | python3 -m json.tool 2>/dev/null || true
        else
            echo "⚠️ Attention: API répond avec le code HTTP $HTTP_CODE"
        fi
    else
        echo "🔴 Processus PID $PID non trouvé."
    fi
else
    echo "⚪ Panel non démarré (aucun fichier PID)."
fi
