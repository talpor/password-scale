import json
import os
import sys
import validators

from flask import Blueprint, abort, request

from server import db, Team, _register_server
from environ import DEMO_SERVER, VERIFICATION_TOKEN

sys.path.insert(1, os.path.join(sys.path[0], '..'))  # noqa
from contrib.slack import error, success, info


view = Blueprint('slack_action', __name__)


@view.route('', methods=['POST'])
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
                'notice, when you want to configure your company server '
                'you should only execute the command `/pass register` along'
                'with the url of your the server.'
            )
