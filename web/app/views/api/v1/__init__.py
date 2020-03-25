from flask import Blueprint

bp = Blueprint('apiV1', __name__)

from app.views.api.v1 import routes
