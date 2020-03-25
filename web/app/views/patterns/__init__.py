from flask import Blueprint

bp = Blueprint('patterns', __name__)

from app.views.patterns import routes
