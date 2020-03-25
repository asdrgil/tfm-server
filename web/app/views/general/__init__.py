from flask import Blueprint

bp = Blueprint('general', __name__)

from app.views.general import routes
