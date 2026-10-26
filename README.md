# 🌐 Nexus Tunnel Control Panel (paweb-xusne)

> **Interface d'administration Web professionnelle pour serveurs V2Ray / VLESS & Nexus Tunnel**  
> Solution complète de gestion multi-comptes, revendeurs, quotas de bande passante et liens d'abonnement.

---

## 📋 Présentation

**Nexus Tunnel Control Panel** est un panneau d'administration moderne basé sur **FastAPI** et **TailwindCSS**, conçu pour gérer simplement des configurations de tunnels **VLESS over WebSocket / CDN / Cloud Run**.

### ✨ Fonctionnalités Clés :
* 👥 **Gestion Multi-Comptes & Rôles :** SuperAdmin, Administrateurs et Revendeurs (gestion des crédits en Go, commissions, sous-comptes).
* ⚡ **Haute performance :** API asynchrone ultra-rapide propulsée par Uvicorn & FastAPI.
* 📊 **Tableau de bord interactif :** Suivi en temps réel de la consommation de bande passante (Up/Down), adresses IP actives, quotas et expiration.
* 📱 **Distribution Client Mobile :** Page de téléchargement intégrée pour l'application Android **Nexus Tunnel (`.apk`)**.
* 🔗 **Générateur de liens & QR Codes :** Liens d'abonnement universels (`/sub/<token>`), configuration VLESS compatible avec v2rayN, V2RayNG, Clash, etc.
* 🎫 **Système de Vouchers / Bons :** Création et activation de codes de recharge prépayés.
* 🛡️ **Sécurité renforcée :** Mots de passe hashés (PBKDF2-HMAC-SHA256), protection anti-brute force, sessions chiffrées.

---

## 🚀 Installation Rapide sur VPS (Ubuntu / Debian)

### Option 1 : Installation automatique en 1 commande *(Recommandé)*

Connectez-vous à votre VPS en SSH (`root`) et lancez :

```bash
curl -sSL https://raw.githubusercontent.com/RootNexTPro/paweb-xusne/main/install.sh | sudo bash
```

Le script installe automatiquement toutes les dépendances, configure l'environnement virtuel Python, active le service d'arrière-plan `systemd` et ouvre le port sur le pare-feu.

---

### Option 2 : Installation manuelle étape par étape

Si vous préférez installer le panel manuellement :

#### 1. Mettre à jour le système et installer les paquets requis
```bash
sudo apt update -y && sudo apt install -y python3 python3-pip python3-venv git curl psmisc
```

#### 2. Cloner le projet dans `/opt/paweb-xusne`
```bash
sudo git clone https://github.com/RootNexTPro/paweb-xusne.git /opt/paweb-xusne
cd /opt/paweb-xusne
```

#### 3. Créer l'environnement virtuel Python et installer les dépendances
```bash
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

#### 4. Rendre les scripts exécutables
```bash
chmod +x *.sh
```

#### 5. Démarrer le panel
```bash
./start_panel.sh
```

---

## 🔑 Identifiants de Connexion par Défaut

Une fois l'installation terminée, ouvrez votre navigateur à l'adresse :  
👉 **`http://<IP_DE_VOTRE_VPS>:8888`**

| Rôle | Nom d'utilisateur | Mot de passe |
| :--- | :--- | :--- |
| **👑 Super Admin** | `superadmin` | `nexus2026!` |
| **🏪 Revendeur (Démo)** | `revendeur_douala` | `reseller123` |

> [!IMPORTANT]
> Changez immédiatement vos mots de passe après votre première connexion depuis la section profil/sécurité du panel.

---

## 🛠️ Gestion au Quotidien

### Si vous utilisez le service `systemd` (Recommandé) :

| Action | Commande |
| :--- | :--- |
| **Vérifier le statut** | `sudo systemctl status nexus-panel` |
| **Démarrer** | `sudo systemctl start nexus-panel` |
| **Arrêter** | `sudo systemctl stop nexus-panel` |
| **Redémarrer** | `sudo systemctl restart nexus-panel` |
| **Consulter les logs en temps réel** | `sudo journalctl -u nexus-panel -f` |

### Si vous utilisez les scripts Bash directs :

```bash
./start_panel.sh     # Démarre le panel en arrière-plan
./status_panel.sh    # Affiche l'état d'exécution et teste l'API HTTP
./stop_panel.sh      # Arrête le serveur
```

---

## ⚙️ Configuration Avancée

### Changer le Port d'écoute

Par défaut, le panel écoute sur le port `8888`. Vous pouvez définir la variable `PANEL_PORT` :

```bash
# Exemple pour lancer sur le port 8080 :
export PANEL_PORT=8080
./start_panel.sh
```

Pour changer le port définitivement avec le service `systemd` :
1. Modifiez `/etc/systemd/system/nexus-panel.service` et changez `Environment=PANEL_PORT=8888` par votre port.
2. Exécutez :
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart nexus-panel
   ```

### Configuration du Pare-feu (si activé)

Si `ufw` est actif sur votre VPS, pensez à autoriser le port :
```bash
sudo ufw allow 8888/tcp
```

---

## 📁 Structure du Projet

```text
paweb-xusne/
├── app.py                 # Serveur FastAPI principal & logique métier
├── requirements.txt       # Dépendances Python (fastapi, uvicorn, qrcode, pillow...)
├── install.sh             # Script d'installation automatique pour VPS
├── start_panel.sh         # Script de démarrage
├── status_panel.sh        # Script de diagnostic et statut
├── stop_panel.sh          # Script d'arrêt
├── static/                # Fichiers statiques et APK client Android
│   ├── NexusTunnel.apk    # Application cliente mobile
│   └── NexusTunnel.app    # Binaire client
├── templates/             # Pages Web (Dashboard, Abonnements, Téléchargements)
│   ├── index.html         # Tableau de bord principal SuperAdmin & Revendeur
│   ├── sub.html           # Interface publique d'abonnement / QR Code
│   └── app.html           # Page de présentation de l'application
└── data/                  # Données persistantes (base JSON locale)
    ├── .gitkeep
    └── database.json.example
```

---

## 📄 Licence

Ce projet est sous licence MIT - libre d'utilisation et de modification pour vos déploiements privés et professionnels.
