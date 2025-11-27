from datetime import timedelta

from quart import Blueprint, current_app, request, jsonify
from quart_rate_limiter import rate_limit

from services.data_manager import DataManager


feeds_api = Blueprint("feeds_api", __name__, url_prefix="/api/feeds")


@feeds_api.route("/categories")
@rate_limit(10, timedelta(seconds=60))
async def get_categories():
    try:
        data_manager = DataManager(current_app.config_quart)
        categories = await data_manager.get_categories()

        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        current_app.config_quart['logger'].error(f"Error getting categories: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@feeds_api.route("/latest")
@rate_limit(10, timedelta(seconds=60))
async def get_latest():
    try:
        limit = request.args.get('limit', default=100, type=int)
        limit = min(max(limit, 1), 1000)

        data_manager = DataManager(current_app.config_quart)
        latest_entries = await data_manager.get_latest_entries(limit)

        return jsonify({
            'success': True,
            'entries': latest_entries,
            'count': len(latest_entries)
        })
    except Exception as e:
        current_app.config_quart['logger'].error(f"Error getting latest entries: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@feeds_api.route("/status")
@rate_limit(5, timedelta(seconds=60))
async def get_status():
    try:
        data_manager = DataManager(current_app.config_quart)
        status = await data_manager.get_status()

        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        current_app.config_quart['logger'].error(f"Error getting status: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
