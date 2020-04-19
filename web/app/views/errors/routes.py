from flask import render_template, request
from flask_login import current_user
from app import db
from app.views.errors import bp

from app.mongoMethods import registerTraceUsers, registerTraceIPs

@bp.before_request
def before_request():
    if current_user.is_authenticated:
        registerTraceUsers(current_user_get_id(), request.endpoint)
    else:
        registerTraceIPs(request.remote_addr, request.endpoint)

@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@bp.app_errorhandler(404)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
