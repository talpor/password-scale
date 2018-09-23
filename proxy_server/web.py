from flask import Blueprint, render_template
from urllib.parse import urlencode

from environ import SLACK_APP_ID, SLACK_CLIENT_ID

privacy_view = Blueprint('privacy', __name__)
landing_view = Blueprint('page_not_found', __name__)


@landing_view.route('', methods=['GET'])
def landing():
    authorize_url = '{}{}'.format(
        'https://slack.com/oauth/authorize?', urlencode({
            'client_id': SLACK_CLIENT_ID,
            'scope': 'commands'
        })
    )

    return render_template(
        'landing.html', authorize_url=authorize_url, app_id=SLACK_APP_ID)


@privacy_view.route('', methods=['GET'])
def privacy():
    return render_template('privacy.html')
