from datetime import datetime
from diskcache import Cache
from flask import Flask, abort, render_template, request
from flask_assets import Environment, Bundle
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
SLACK_APP_ID = '2554558892.385841792964'

secret_key = generate_key(os.environ.get('SECRET_KEY'))
private_key = secret_key.exportKey("PEM")
public_key = secret_key.publickey().exportKey("PEM")

application = Flask(__name__)
application.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

assets = Environment(application)
cache = Cache('/tmp/tokencache')
cmd = PasswordScaleCMD(cache, private_key)
db = SQLAlchemy(application)

all_css = Bundle(
    'css/base.scss',
    'css/insert.scss',
    filters='scss',
    output='dist/all.css'
)
insert_js = Bundle(
    'js/wordlist.js',
    'js/insert.js',
    filters='babel',
    output='dist/scripts.js'
)
assets.register('css_all', all_css)
assets.register('js_insert', insert_js)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.String, unique=True)
    url = db.Column(db.String, nullable=True)
    public_key = db.Column(db.Text, nullable=True)
    created = db.Column(db.DateTime)

    def api(self, path):
        url_parts = list(urlparse(self.url))
        url_parts[2] = os.path.join(url_parts[2], path)
        return urlunparse(url_parts)

    def __init__(self, team_id, created=None):
        self.team_id = team_id
        if self.created is None:
            self.created = datetime.utcnow()

    def __repr__(self):
        return 'Slack team: {}'.format(self.team_id)


@application.route('/public_key', methods=['GET'])
def get_public_key():
    return public_key


@application.route('/slack/command', methods=['POST'])
def api():
    data = request.values.to_dict()
    command = re.split('\s+', data['text'])
    team_id = data['team_id']
    team_domain = data['team_domain']
    channel = data['channel_id']

    # ensuring that the request comes from slack
    if data['token'] != VERIFICATION_TOKEN:
        return abort(404)

    team = db.session.query(Team).filter_by(team_id=team_id).first()

    if command[0] == 'help':
        return 'WIP: https://github.com/talpor/password-scale'

    if command[0] == 'register' and len(command) == 2:
        url = command[1]
        if not validators.url(url):
            return 'Invalid URL format, use: https://<domain>'

        team.url = url
        response = requests.get(team.api('public_key'))

        if response.status_code != requests.codes.ok:
            return ('Unable to retrieve the public_key '
                    'from the server').format(team_domain)

        team.public_key = response.text
        db.session.commit()

        return '{} team successfully registered!'.format(team_domain)

    if not team.url:
        return ('{} team does not have a password server registered, use '
                'the command `/pass register https://your.password.server` '
                'to start, check the configuration guide -> '
                'https://github.com/talpor/password-scale/blob/master'
                '/README.md').format(team_domain)

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
        secret = request.form['secret']
        encrypted = 'encrypted' in request.form
        if not encrypted:
            # if javascript is disabled then the message comes unencrypted
            secret = encrypt(secret, team.public_key)
        try:
            cmd.insert(token, secret)
        except PasswordScaleError as e:
            abort(e.message)

        return render_template('success.html')

    else:
        return render_template(
            'insert.html',
            secret=re.sub('[a-zA-Z0-9]+\/', '', path, 1),
            public_key=team.public_key
        )
    abort(404)


@application.route('/slack/oauth', methods=['GET'])
def slack_oauth():
    if 'code' not in request.args:
        abort(400)

    oauth_access_url = '{}{}'.format(
        'https://slack.com/api/oauth.access?', urlencode({
            'client_id': SLACK_APP_ID,
            'client_secret': SLACK_APP_SECRET,
            'code': request.args['code']
        })
    )
    response = requests.get(oauth_access_url).json()
    if 'ok' not in response or not response['ok']:
        abort(403)

    # deliberately does not store the `access_token` may be will be useful
    # for a future feature but right now it is not necessary :thinking_face:

    new_team = Team(
        team_id=response['team_id'],
        # access_token=response.json()['access_token'],
    )

    db.session.add(new_team)
    db.session.commit()

    return render_template('success.html')


@application.route('/', methods=['GET'])
def landing():
    authorize_url = '{}{}'.format(
        'https://slack.com/oauth/authorize?', urlencode({
            'client_id': SLACK_APP_ID,
            'scope': 'commands'
        })
    )

    return render_template('landing.html', authorize_url=authorize_url)


@application.route('/privacy', methods=['GET'])
def privacy():
    return render_template('privacy.html')


if __name__ == '__main__':
    application.run(host="0.0.0.0", debug=True)
