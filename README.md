# IT Monitoring

Dashboard de veille technologique qui agrège les flux RSS de projets IT (Proxmox, Docker, Pterodactyl, Go, Python) et envoie des notifications Discord.

## Fonctionnalités

- Agrégation de flux RSS/Atom (releases, annonces, commits)
- Interface web avec filtres par catégorie et type
- Notifications Discord avec boutons cliquables
- Stockage SQLite
- Marquage lu/non-lu persistant (localStorage)

## Installation

```bash
# Cloner le repo
git clone https://github.com/votre-repo/IT-monitoring.git
cd IT-monitoring

# Créer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec votre webhook Discord
```

## Configuration

### Variables d'environnement (.env)

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Fichiers de configuration

- `config.json` - Configuration production
- `config_dev.json` - Configuration développement

Options principales :
- `discord.enabled` - Activer les notifications Discord
- `discord.site_url` - URL du dashboard (pour les liens Discord)
- `discord.webhooks` - Liste des webhooks avec filtres
- `rss_feeds` - Flux RSS à surveiller
- `fetch_interval` - Intervalle de récupération (secondes)

## Lancement

### Avec Docker (recommandé)

```bash
# Configurer le webhook
cp .env.example .env
# Éditer .env

# Lancer
docker compose up -d

# Voir les logs
docker compose logs -f
```

### Sans Docker

```bash
# Mode développement
set DEV=True && python main.py  # Windows
DEV=True python main.py  # Linux/Mac

# Mode production
set DEV=False && python main.py
```

Le serveur démarre sur `http://localhost:25567`.

## Structure

```
IT-monitoring/
├── main.py              # Point d'entrée
├── config.json          # Config production
├── config_dev.json      # Config développement
├── Dockerfile
├── docker-compose.yml
├── services/
│   ├── database.py      # Gestion SQLite
│   ├── rss_fetcher.py   # Récupération RSS
│   ├── discord_notifier.py  # Notifications Discord
│   └── background_tasks.py  # Tâches périodiques
├── endpoints/
│   └── api/feeds.py     # API REST
├── static/              # Assets production (minifiés)
├── static_dev/          # Assets développement
│   ├── js/app.js
│   └── css/style.css
└── data/
    └── feeds.db         # Base SQLite
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/feeds/latest` | Dernières entrées |
| `GET /api/feeds/status` | Statistiques |
| `GET /api/feeds/categories` | Liste des catégories |

## License

MIT
