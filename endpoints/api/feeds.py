from datetime import timedelta

from quart import Blueprint, current_app, request, jsonify
from quart_rate_limiter import rate_limit

from services.data_manager import DataManager
from utility.utils import get_client_ip


feeds_api = Blueprint("feeds_api", __name__, url_prefix="/api/feeds")


@feeds_api.route("/categories")
@rate_limit(10, timedelta(seconds=60))
async def get_categories():
    try:
        data_manager = DataManager(current_app.config_quart)
        feeds_data = await data_manager.load_feeds_data()

        categories = {}
        for category_key, category_data in feeds_data.items():
            categories[category_key] = {
                'name': category_data['category'],
                'last_update': category_data.get('last_update'),
                'feeds_count': len(category_data.get('feeds', {}))
            }

        user_ip = get_client_ip()
        await data_manager.save_user_activity(user_ip, 'view_categories')

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


@feeds_api.route("/category/<category>")
@rate_limit(10, timedelta(seconds=60))
async def get_category(category):
    try:
        data_manager = DataManager(current_app.config_quart)
        category_data = await data_manager.get_category_data(category)

        if not category_data:
            return jsonify({
                'success': False,
                'error': 'Category not found'
            }), 404

        user_ip = get_client_ip()
        await data_manager.save_user_activity(user_ip, 'view_category', {'category': category})

        return jsonify({
            'success': True,
            'data': category_data
        })
    except Exception as e:
        current_app.config_quart['logger'].error(f"Error getting category {category}: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@feeds_api.route("/category/<category>/feed/<feed>")
@rate_limit(10, timedelta(seconds=60))
async def get_feed(category, feed):
    try:
        data_manager = DataManager(current_app.config_quart)
        feed_data = await data_manager.get_feed_data(category, feed)

        if not feed_data:
            return jsonify({
                'success': False,
                'error': 'Feed not found'
            }), 404

        user_ip = get_client_ip()
        await data_manager.save_user_activity(user_ip, 'view_feed', {
            'category': category,
            'feed': feed
        })

        return jsonify({
            'success': True,
            'data': feed_data
        })
    except Exception as e:
        current_app.config_quart['logger'].error(f"Error getting feed {category}/{feed}: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@feeds_api.route("/latest")
@rate_limit(10, timedelta(seconds=60))
async def get_latest():
    try:
        limit = request.args.get('limit', default=20, type=int)
        limit = min(max(limit, 1), 100)  # Entre 1 et 100

        data_manager = DataManager(current_app.config_quart)
        latest_entries = await data_manager.get_latest_entries(limit)

        user_ip = get_client_ip()
        await data_manager.save_user_activity(user_ip, 'view_latest', {'limit': limit})

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
        feeds_data = await data_manager.load_feeds_data()

        total_categories = len(feeds_data)
        total_feeds = sum(len(cat.get('feeds', {})) for cat in feeds_data.values())
        total_entries = sum(
            sum(len(feed.get('entries', [])) for feed in cat.get('feeds', {}).values())
            for cat in feeds_data.values()
        )

        last_updates = []
        for category_data in feeds_data.values():
            if 'last_update' in category_data:
                last_updates.append(category_data['last_update'])

        last_global_update = max(last_updates) if last_updates else None

        return jsonify({
            'success': True,
            'status': {
                'total_categories': total_categories,
                'total_feeds': total_feeds,
                'total_entries': total_entries,
                'last_update': last_global_update
            }
        })
    except Exception as e:
        current_app.config_quart['logger'].error(f"Error getting status: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500