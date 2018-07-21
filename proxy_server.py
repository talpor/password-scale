from datetime import datetime
from diskcache import Cache
from flask import Flask, abort, render_template, request
from flask import jsonify
from flask_assets import Environment, Bundle
from flask_sqlalchemy import SQLAlchemy
from raven.contrib.flask import Sentry
from urllib.parse import urlparse, urlunparse, urlencode

from contrib.crypto import generate_key, encrypt
from contrib.slack import warning, error, success, info
from password_scale.core import PasswordScaleCMD, PasswordScaleError

import json
import os
import re
import requests
import validators

DEMO_SERVER = os.environ.get('DEMO_SERVER')
SITE = os.environ.get('SITE')
SLACK_APP_ID = os.environ.get('SLACK_APP_ID', '2554558892.385841792964')
SLACK_APP_SECRET = os.environ.get('SLACK_APP_SECRET')
VERIFICATION_TOKEN = os.environ.get('VERIFICATION_TOKEN')

secret_key = generate_key(os.environ.get('BIP39'))
private_key = secret_key.exportKey("PEM")
public_key = secret_key.publickey().exportKey("PEM")

server = Flask(__name__)
server.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

assets = Environment(server)
cache = Cache('/tmp/tokencache')
sentry = Sentry(server, dsn=os.environ.get('SENTRY_DSN'))

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
assets.register('css_all', all_css)
assets.register('js_insert', insert_js)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slack_id = db.Column(db.String, unique=True)
    domain = db.Column(db.String, unique=True)
    url = db.Column(db.String, nullable=True)
    public_key = db.Column(db.Text, nullable=True)
    created = db.Column(db.DateTime)

    def api(self, path):
        url_parts = list(urlparse(self.url))
        url_parts[2] = os.path.join(url_parts[2], path)
        return urlunparse(url_parts)

    def __init__(self, slack_id, domain, created=None):
        self.slack_id = slack_id
        self.domain = domain
        if self.created is None:
            self.created = datetime.utcnow()

    def __repr__(self):
        return 'Slack team: {}'.format(self.domain)


def _register_server(url, team):
    team.url = url
    try:
        response = requests.get(team.api('public_key'))
    except requests.exceptions.ConnectionError:
        return False

    if response.status_code != requests.codes.ok:
        return False

    team.public_key = response.text
    db.session.commit()
    return True


@server.route('/public_key', methods=['GET'])
def get_public_key():
    return public_key


@server.route('/slack/action', methods=['POST'])
def action_api():
    data = request.values.to_dict()
    payload = json.loads(data['payload'])
    if payload['token'] != VERIFICATION_TOKEN:
        return abort(404)

    if 'actions' not in payload:
        return 'not implemented'

    option = payload['actions'][0]
    action = option['name']

    if payload['callback_id'] == 'configure_password_server':
        if action == 'no_reconfigure':
            return info('Password server unchanged.')

        elif action == 'no_configure':
            return success(
                'Sure! for more information about the pass command working '
                'check `/pass help` or our web page in '
                'https://scale.talpor.com'
            )

        team = db.session.query(Team).filter_by(
            slack_id=payload['team']['id']).first()

        if action == 'reconfigure_server':
            if not validators.url(option['value']):
                return error('Invalid URL format, use: https://<domain>')

            if not _register_server(option['value'], team):
                return error(
                    'Unable to retrieve the _public_key_ '
                    'from the server'.format(payload['team']['domain'])
                )
            return success('Password server successfully updated!')

        elif action == 'use_demo_server':
            if not _register_server(DEMO_SERVER, team):
                return error(
                    'An error occurred registering the server, '
                    'please try later.'
                )
            return success(
                'The testing server is already configured! remember that '
                'the data on this server can be deleted without prior '
                'notice, when you want to configure your final server '
                'you should only execute the command `/pass register` again.'
            )


@server.route('/slack/command', methods=['POST'])
def api():
    data = request.values.to_dict()
    try:
        command = re.split('\s+', data['text'])
        slack_id = data['team_id']
        team_domain = data['team_domain']
        channel = data['channel_id']
    except KeyError:
        abort(400)

    # ensuring that the request comes from slack
    if 'token' not in data or data['token'] != VERIFICATION_TOKEN:
        return abort(404)

    team = db.session.query(Team).filter_by(slack_id=slack_id).first()
    if not team:
        return error(
            'You are not registered in our proxy server, try removig the app '
            'and adding it to slack again.'
        )

    if command[0] == 'help':
        fields = [
            {
                'title': '`/pass` _or_ `/pass list`',
                'value': 'To list the available passwords in this channel.',
                'short': True
            },
            {
                'title': '`/pass <secret>` or `/pass show <secret>`',
                'value': (
                    'To retrieve a one time use link with the secret content, '
                    'this link expires in 15 minutes.'
                ),
                'short': True
            },
            {
                'title': '`/pass <secret>`',
                'value': (
                    'To retrieve a one time use link with the secret content, '
                    'this link expires in 15 minutes.'
                ),
                'short': True
            },
            {
                'title': '`/pass insert <secret>`',
                'value': (
                    'To retrieve the link with the editor to create the '
                    'secret, this link expires in 15 minutes.'
                ),
                'short': True
            },
            {
                'title': '`/pass remove <secret>`',
                'value': (
                    'To make unreachable the secret, to complete deletion is '
                    'necessary doing it manually from the s3 password storage.'
                ),
                'short': True
            },
            {
                'title': '`/pass register <password_server_url>`',
                'value': (
                    'To setup the password storage, it is only necessary '
                    'to execute it once.'
                ),
                'short': True
            }
        ]
        return jsonify({
            'attachments': [
                {
                    'fallback': (
                        '_Usage:_ https://github.com/talpor/password-scale'
                    ),
                    'text': '*_Usage:_*',
                    'fields': fields
                }
            ]
        })

    if command[0] == 'register' and len(command) == 2:
        url = command[1]
        if not validators.url(url):
            return error('Invalid URL format, use: https://<domain>')

        if team.url:
            msg = ('This team is already registered, you want to replace '
                   'the password server?')
            return jsonify({
                'attachments': [
                    {
                        'fallback': 'This team already registered',
                        'text': msg,
                        'callback_id': 'configure_password_server',
                        'color': 'warning',
                        'actions': [
                            {
                                'name': 'reconfigure_server',
                                'text': 'Yes',
                                'type': 'button',
                                'value': url
                            },
                            {
                                'name': 'no_reconfigure',
                                'text': 'No',
                                'style': 'danger',
                                'type': 'button',
                                'value': 'no'
                            },
                        ]
                    }
                ]
            })

        if not _register_server(url, team):
            return error(
                'Unable to retrieve the _public_key_ '
                'from the server'.format(team_domain)
            )

        return success('{} team successfully registered!'.format(team_domain))

    if not team.url:
        msg = (
            '*{}* team does not have a password server registered, use '
            'the command `/pass register https://your.password.server` '
            'to configure yours.'.format(team_domain)
        )
        warning_msg = (
            'The idea of the testing server is that you be able to try '
            'the _Password Scale_ command working. For daily use among '
            'the team members is necessary to configure your own. '
            '*Any information stored on this server can be deleted at '
            'any moment without prior notice!*'
        )
        return jsonify({
            'attachments': [
                {
                    'fallback': msg,
                    'text': msg,
                    'color': 'warning',
                    'callback_id': 'configure_password_server',
                    'actions': [
                        {
                            'text': 'Check the configuration guide',
                            'type': 'button',
                            'url': ('https://github.com/talpor/'
                                    'password-scale/blob/master/README.md')
                        },
                        {
                            'name': 'use_demo_server',
                            'text': 'Use testing server',
                            'type': 'button',
                            'value': 'no',
                            'confirm': {
                                'title': 'Are you sure?',
                                'text': warning_msg,
                                'ok_text': 'I understand',
                                'dismiss_text': 'No'
                            }
                        },
                        {
                            'name': 'no_configure',
                            'text': 'Later',
                            'type': 'button',
                            'value': 'no'
                        }
                    ]
                }
            ]
        })
        return warning(
            '{} team does not have a password server registered, use '
            'the command `/pass register https://your.password.server` '
            'to start, check the configuration guide -> '
            'https://github.com/talpor/password-scale/blob/master'
            '/README.md'.format(team_domain)
        )
    if command[0] in ['', 'list']:
        try:
            dir_ls = cmd.list(team, channel)
        except PasswordScaleError as e:
            return error('_{}_'.format(e.message))

        if not dir_ls:
            return warning(
                'You have not passwords created for this channel, use '
                '`/pass insert <secret>` to create the first one!'
            )

        return jsonify({
            'attachments': [
                {
                    'fallback': dir_ls,
                    'text': 'Password Store\n{}'.format(dir_ls),
                    'footer': (
                        'Use the command `/pass <key_name>` to retrieve '
                        'some of the keys'
                    )
                }
            ]
        })
        return info('Password Store\n{}'.format(dir_ls))

    if command[0] == 'insert' and len(command) == 2:
        app = command[1]
        token = cmd.generate_insert_token(team, channel, app)

        msg = 'Adding password for *{}* in this channel'.format(app)
        return jsonify({
            'attachments': [
                {
                    'fallback': msg,
                    'text': msg,
                    'footer': 'This editor will be valid for 15 minutes',
                    'color': 'good',
                    'actions': [
                        {
                            'text': 'Open editor',
                            'style': 'primary',
                            'type': 'button',
                            'url': '{}/insert/{}'.format(SITE, token)
                        }
                    ]
                }
            ]
        })

    if command[0] == 'remove' and len(command) == 2:
        app = command[1]
        if cmd.remove(team, channel, app):
            return success(
                'Now the password *{}* is unreachable, to complete '
                'removal contact the system administrator.'.format(app)
            )
        return warning(
            'Looks like this secret is not in your repository '
            ':thinking_face: use the list command `pass list {}` '
            'to verify your storage.'.format(app))

    if command[0] == 'show' and len(command) == 2:
        app = command[1]
    else:
        app = command[0]

    onetime_link = cmd.show(team, channel, app)
    if onetime_link:
        return jsonify({
            'attachments': [
                {
                    'fallback': 'Password: {}'.format(onetime_link),
                    'text': 'Password for *{}*'.format(app),
                    'footer': 'This secret will be valid for 15 minutes',
                    'color': 'good',
                    'actions': [
                        {
                            'text': 'Open secret',
                            'style': 'primary',
                            'type': 'button',
                            'url': onetime_link
                        }
                    ]
                }
            ]
        })
    else:
        return warning('*{}* is not in the password store.'.format(app))


@server.route('/insert/<token>', methods=['GET', 'POST'])
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

        message = ('Your secret was securely stored!')
        return render_template('success.html', message=message)

    else:
        return render_template(
            'insert.html',
            secret=re.sub('[a-zA-Z0-9]+\/', '', path, 1),
            public_key=team.public_key
        )
    abort(404)


@server.route('/slack/oauth', methods=['GET'])
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
        sentry.captureMessage(response)
        abort(403)

    slack_id = response['team_id']

    if not db.session.query(Team).filter_by(slack_id=slack_id).first():
        # deliberately does not store the `access_token` may be will be useful
        # for a future feature but right now it is not necessary
        new_team = Team(
            slack_id=slack_id,
            domain=response['team_domain']
            # access_token=response.json()['access_token'],
        )
        db.session.add(new_team)
        db.session.commit()
    message = ('The Slack application was installed successfully, go to your '
               'Slack group and try it!')
    return render_template('success.html', message=message)


@server.route('/', methods=['GET'])
def landing():
    authorize_url = '{}{}'.format(
        'https://slack.com/oauth/authorize?', urlencode({
            'client_id': SLACK_APP_ID,
            'scope': 'commands'
        })
    )

    return render_template('landing.html', authorize_url=authorize_url)


@server.route('/privacy', methods=['GET'])
def privacy():
    return render_template('privacy.html')


@server.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    server.run(host='0.0.0.0')
