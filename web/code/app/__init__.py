from flask import Flask
from config import Config
from pymongo import MongoClient


app = Flask(__name__)
app.config.from_object(Config)
client = MongoClient('localhost', 27017)
db = client['tfm']

from app import routes
