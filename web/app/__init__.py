#import logging
#from logging.handlers import SMTPHandler, RotatingFileHandler
#import os
from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from flask_socketio import SocketIO
from threading import Lock
from app.constants import urlPrefix

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = "{}/iniciarSesion".format(urlPrefix)
login.login_message = u"Por favor, inicia sesión para poder acceder a esta página"

thread = None
thread_lock = Lock()
socketio = SocketIO(app)



if not app.debug:
    '''
    if app.config['MAIL_SERVER']:
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr='no-reply@' + app.config['MAIL_SERVER'],
            toaddrs=app.config['ADMINS'], subject='Tfm Failure',
            credentials=auth, secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)
    '''

    #CONFIGURE LOGS

    '''
    if not os.path.exists('logs'):
        os.mkdir('logs')
        os.mkdir('logs/general')
        os.mkdir('logs/registered')
        os.mkdir('logs/unregistered')

    file_handler = RotatingFileHandler('logs/general/tfm.log', maxBytes=102400,
                                       backupCount=40)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Tfm startup')
    '''

from app.views.api.v1 import bp as apiV1_bp
from app.views.ajax import bp as ajax_bp
from app.views.auth import bp as auth_bp
from app.views.errors import bp as errors_bp
from app.views.general import bp as general_bp  
from app.views.groups import bp as groups_bp
from app.views.patients import bp as patients_bp
from app.views.patterns import bp as patterns_bp


app.register_blueprint(apiV1_bp)
app.register_blueprint(ajax_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(errors_bp)
app.register_blueprint(general_bp)
app.register_blueprint(groups_bp)
app.register_blueprint(patients_bp)
app.register_blueprint(patterns_bp)
