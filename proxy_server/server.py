import os
import redis
import requests
import sys

from datetime import datetime
from flask import Flask
from flask_assets import Environment, Bundle
from flask_sqlalchemy import SQLAlchemy
from raven.contrib.flask import Sentry
from urllib.parse import urlparse, urlunparse

from environ import BIP39, DATABASE_URL, SENTRY_DSN

sys.path.insert(1, os.path.join(sys.path[0], '..'))
from contrib.crypto import generate_key  # noqa
from password_scale.core import PasswordScaleCMD  # noqa


secret_key = generate_key(BIP39)
private_key = secret_key.exportKey("PEM")
public_key = secret_key.publickey().exportKey("PEM")

server = Flask(__name__)
server.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

assets = Environment(server)
cache = redis.StrictRedis(host='redis', port=6379)
sentry = Sentry(server, dsn=SENTRY_DSN)

cmd = PasswordScaleCMD(cache, private_key)
db = SQLAlchemy(server)

all_css = Bundle(
    'css/reset.scss',
    'css/base.scss',
    'css/insert.scss',
    'css/landing.scss',
    'css/privacy.scss',
    filters='node-scss',
    output='dist/all.css'
)
insert_js = Bundle(
    'js/wordlist.js',
    'js/insert.js',
    filters='babel',
    output='dist/scripts.js'
)
landing_js = Bundle(
    'js/landing.js',
    filters='babel',
    output='dist/landing.js'
)
assets.register('css_all', all_css)
assets.register('js_insert', insert_js)
assets.register('js_landing', landing_js)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slack_id = db.Column(db.String, unique=True)
    name = db.Column(db.String, unique=True)
    url = db.Column(db.String, nullable=True)
    public_key = db.Column(db.Text, nullable=True)
    created = db.Column(db.DateTime)

    def register_server(self, url):
        self.url = url
        try:
            response = requests.get(self.api('public_key'))
        except requests.exceptions.ConnectionError:
            return False

        if response.status_code != requests.codes.ok:
            return False

        self.public_key = response.text
        db.session.commit()
        return True

    def api(self, path):
        url_parts = list(urlparse(self.url))
        url_parts[2] = os.path.join(url_parts[2], path)
        return urlunparse(url_parts)

    def __init__(self, slack_id, name, created=None):
        self.slack_id = slack_id
        self.name = name
        if self.created is None:
            self.created = datetime.utcnow()

    def __repr__(self):
        return 'Slack team: {}'.format(self.name)
