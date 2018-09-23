import os
from dotenv import load_dotenv

load_dotenv()

BIP39 = os.environ.get('BIP39')
DATABASE_URL = os.environ.get('DATABASE_URL')
DEMO_SERVER = os.environ.get('DEMO_SERVER', 'http://0.0.0.0:8090/')
SENTRY_DSN = os.environ.get('SENTRY_DSN')
SITE = os.environ.get('SITE')
SLACK_APP_ID = os.environ.get('SLACK_APP_ID', 'ABBQRPAUC')
SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID', '2554558892.385841792964')
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
SLACK_CLIENT_SECRET = os.environ.get('SLACK_CLIENT_SECRET')
VERIFICATION_TOKEN = os.environ.get('VERIFICATION_TOKEN')
