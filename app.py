from datetime import datetime
from diskcache import Cache
from flask import abort
from flask import Flask, request
from flask import render_template
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse, urlunparse, urlencode

from contrib.crypto import generate_key, encrypt
from password_scale import PasswordScaleCMD, PasswordScaleError

import os
import re
import requests
import validators

SITE = os.environ.get('SITE')
VERIFICATION_TOKEN = os.environ.get('VERIFICATION_TOKEN')
SLACK_APP_SECRET = os.environ.get('SLACK_APP_SECRET')

secret_key = generate_key(os.environ.get('SECRET_KEY'))
private_key = secret_key.exportKey("PEM")
public_key = secret_key.publickey().exportKey("PEM")

application = Flask(__name__)
application.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(application)
cache = Cache('/tmp/tokencache')
cmd = PasswordScaleCMD(db, cache, private_key)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    url = db.Column(db.String)
    public_key = db.Column(db.Text)
    created = db.Column(db.DateTime)

    def api(self, path):
        url_parts = list(urlparse(self.url))
        url_parts[2] = os.path.join(url_parts[2], path)
        return urlunparse(url_parts)

    def __init__(self, name, url, public_key, created=None):
        self.name = name
        self.url = url
        self.public_key = public_key
        if self.created is None:
            self.created = datetime.utcnow()

    def __repr__(self):
        return self.name


@application.route('/public_key', methods=['GET'])
def get_public_key():
    return public_key


@application.route('/slack/command', methods=['POST'])
def api():
    data = request.values.to_dict()
    command = re.split('\s+', data['text'])
    team_domain = data['team_domain']

    # ensuring that the request comes from slack
    if data['token'] != VERIFICATION_TOKEN:
        return abort(404)

    channel = data['channel_id']

    if command[0] == 'help':
        return 'WIP: https://github.com/talpor/password-scale'

    elif command[0] == 'register' and len(command) == 2:
        url = command[1]
        if not validators.url(url):
            return 'Invalid URL format, use: https://<domain>'
        new_team = Team(
            name=team_domain,
            url=url,
            public_key=''
        )
        try:
            cmd.register(new_team)
        except PasswordScaleError as e:
            return e.message

        return '{} team successfully registered!'.format(team_domain)

    team = db.session.query(Team).filter_by(name=team_domain).first()
    if not team:
        return ('{} team is not registered, use the command `/pass register '
                'https://your.password.application` to start, see the '
                'configuration guide -> https://github.com/talpor/'
                'password-scale/blob/master/README.md').format(team_domain)

    if command[0] in ['', 'list']:
        dir_ls = cmd.list(team, channel)
        return '```{}```'.format(dir_ls)

    if command[0] == 'insert' and len(command) == 2:
        app = command[1]
        valid_path = cmd.generate_insert_token(team, channel, app)
        return 'Add _{}_ password in: {}/insert/{}'.format(
            app, SITE, valid_path)

    if command[0] == 'remove' and len(command) == 2:
        app = command[1]
        valid_path = cmd.remove(team, channel, app)
        return ('Now the password _{}_ is unreachable, to complete removal '
                'contact the system administrator.').format(app)

    if command[0] == 'show' and len(command) == 2:
        app = command[1]
    else:
        app = command[0]

    onetime_link = cmd.show(team, channel, app)
    if onetime_link:
        return 'Password for _{}_: {}'.format(app, onetime_link)
    else:
        return '_{}_ is not in the password store.'.format(app)


@application.route('/insert/<token>', methods=['GET', 'POST'])
def insert(token):
    token = str(token)
    if token not in cache:
        abort(400 if request.method == 'POST' else 404)

    path = cache[token]['path']
    team_id = cache[token]['team_id']
    team = db.session.query(Team).filter_by(id=team_id).first()

    if request.method == 'POST':
        secret = request.form['secret'].replace('EOF', '')

        try:
            # TODO: move encryption to the frontend
            cmd.insert(token, encrypt(secret, team.public_key))
        except PasswordScaleError as e:
            abort(e.message)

        return 'ok'

    else:
        return render_template('insert.html', secret=re.sub(
            '[a-zA-Z0-9]+\/', '', path, 1))
    abort(404)


@application.route('/', methods=['GET'])
def landing():
    client_id = '235505574834.384094057591'
    client_secret = SLACK_APP_SECRET
    authorize_url = '{}{}'.format(
        'https://slack.com/oauth/authorize?', urlencode({
            'client_id': client_id,
            'scope': 'commands'
        })
    )
    if 'code' in request.form:
        oauth_access_url = '{}{}'.format(
            'https://slack.com/api/oauth.access?', urlencode({
                'client_id': client_id,
                'client_secret': client_secret,
                'code': request.form['code']
            })
        )
        response = requests.get(oauth_access_url)
        # TODO: save access_token from response in Team model
    return render_template('landing.html', authorize_url=authorize_url)


if __name__ == '__main__':
    application.run()
