import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = 'unnecesaryPass' #Required to avoid CSRF errors
