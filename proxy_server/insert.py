import os
import pickle
import re
import sys

from flask import Blueprint, abort, request, render_template
from server import db, Team, cache, cmd

sys.path.insert(1, os.path.join(sys.path[0], '..'))  # noqa
from contrib.crypto import encrypt
from password_scale.core import PasswordScaleError

view = Blueprint('insert', __name__)


@view.route('/<token>', methods=['GET', 'POST'])
def insert(token):
    token = str(token)
    if token not in cache:
        abort(400 if request.method == 'POST' else 404)

    obj = pickle.loads(cache[token])

    path = obj['path']
    team_id = obj['team_id']
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

        message = (
            'Your secret was securely stored! Return to Slack and check it '
            'out by doing /pass list')
        return render_template('success.html', message=message)

    else:
        return render_template(
            'insert.html',
            secret=re.sub('[a-zA-Z0-9]+\/', '', path, 1),
            public_key=team.public_key
        )
    abort(404)
