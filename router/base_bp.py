from datetime import timedelta

from quart import Blueprint, current_app, render_template
from quart_rate_limiter import rate_limit


base_bp = Blueprint("base", __name__)


@base_bp.route("/")
@rate_limit(2, timedelta(seconds=1))
async def home():
    config_quart = current_app.config_quart  # noqa
    return await render_template("index.html")
