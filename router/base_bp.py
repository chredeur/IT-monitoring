from datetime import datetime, timedelta, timezone

from quart import Blueprint, current_app, render_template, jsonify
from quart_rate_limiter import rate_limit


base_bp = Blueprint("base", __name__)


@base_bp.route("/")
@rate_limit(2, timedelta(seconds=1))
async def home():
    config_quart = current_app.config_quart  # noqa
    return await render_template("index.html")


@base_bp.route("/api/health")
@rate_limit(30, timedelta(seconds=60))
async def health_check():
    """Endpoint de health check pour le monitoring externe."""
    try:
        config = current_app.config_quart
        background_manager = config.get('background_manager')

        status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '1.0.0',
            'services': {
                'background_tasks': background_manager.running if background_manager else False,
                'discord_notifications': config.get('discord', {}).get('enabled', False)
            }
        }

        return jsonify(status)

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e)
        }), 500
