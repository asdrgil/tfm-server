from flask import Blueprint

bp = Blueprint('groups', __name__)

from app.views.groups import routes
