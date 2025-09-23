from datetime import timedelta

from quart import Blueprint, current_app, jsonify
from quart_rate_limiter import rate_limit

from services.data_manager import DataManager
from utility.utils import get_client_ip


admin_api = Blueprint("admin_api", __name__, url_prefix="/api/admin")


@admin_api.route("/force-fetch", methods=["POST"])
@rate_limit(2, timedelta(minutes=5))
async def force_fetch():
    try:
        background_manager = current_app.config_quart.get('background_manager')

        if not background_manager:
            return jsonify({
                'success': False,
                'error': 'Background manager not available'
            }), 503

        success = await background_manager.force_fetch()

        user_ip = get_client_ip()
        data_manager = DataManager(current_app.config_quart)
        await data_manager.save_user_activity(user_ip, 'force_fetch', {'success': success})

        return jsonify({
            'success': success,
            'message': 'Fetch completed' if success else 'Fetch failed'
        })

    except Exception as e:
        current_app.config_quart['logger'].error(f"Error in force fetch: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@admin_api.route("/user-activity")
@rate_limit(5, timedelta(minutes=1))
async def get_user_activity():
    try:
        data_manager = DataManager(current_app.config_quart)
        activities = await data_manager.load_user_activities()

        recent_activities = activities[-100:]

        user_ip = get_client_ip()
        await data_manager.save_user_activity(user_ip, 'view_admin_activity')

        return jsonify({
            'success': True,
            'activities': recent_activities,
            'count': len(recent_activities)
        })

    except Exception as e:
        current_app.config_quart['logger'].error(f"Error getting user activity: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500