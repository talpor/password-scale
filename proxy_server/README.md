# Password Scale - Proxy Server

### Requirements

#### Installed software
- virtualenv + virtualenvwrapper (https://github.com/brainsik/virtualenv-burrito)
- python3
- docker/docker-compose (optional)

## Instalation

- Create a virtual environment `mkvirtualenv password-scale-ps -p python3`
- Install dependencies `pip install -r requirements/proxy-server.txt`
- Create _proxy_server/.env_ file based on _proxy_server/example.env
- Create the database specified in _DATABASE_URL_ and create the scheme doing `import server; server.db.create_all()` from a python shell in _proxy_server_ directory
- Run the server using the command `python proxy_server` for development or `gunicorn --bind 0.0.0.0:8000 wsgi` for production

## Running using docker

- Create _proxy_server/.env_ file based on _proxy_server/example.env_
- Run `docker-compose up`

### Environment variables table

| Key | Description |
| --- | ----------- |
| BIP39 | Mnemonic code for generating deterministic keys, specification: https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki |
| DEMO_SERVER | URL of the password storage server, this URL is used to setup the command for testing purposes |
| DATABASE_URL | Database URL where is stored the password storage server addresses of each client |
| SENTRY_DSN | Configuration required by the Sentry SDKs |
| SITE | URL of this server, it is used by the command to show the insert password editor URL |
| SLACK_CLIENT_ID | Slack Client ID |
| SLACK_CLIENT_SECRET | Slack APP Secret |
| VERIFICATION_TOKEN | Slack Verification Token |
