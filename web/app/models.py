from datetime import datetime
from hashlib import md5
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    surname1 = db.Column(db.String(64), index=True)
    surname2 = db.Column(db.String(64), index=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)


    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def set_surname1(self, surname1):
        self.surname1 = surname1

    def get_surname1(self):
        return self.surname1

    def set_surname2(self, surname2):
        self.surname2 = surname2

    def get_surname2(self):
        return self.surname2

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.id
    '''
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)
    '''

@login.user_loader
def load_user(id):
    return User.query.get(int(id))
