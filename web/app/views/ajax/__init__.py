from flask import Blueprint

bp = Blueprint('ajax', __name__)

from app.views.ajax import routes
