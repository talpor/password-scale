FROM python:3.9-alpine

COPY . /app

RUN apk update
RUN apk add \
    g++ \
    gcc \
    libressl-dev \
    make \
    nodejs \
    nodejs-npm \
    postgresql-dev \
    python-dev

RUN npm install -g yarn
RUN yarn global add babel-cli
RUN yarn global add node-sass

WORKDIR /app
RUN pip install -r requirements/proxy-server.txt
RUN yarn

EXPOSE 8000

WORKDIR /app/slack_server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "wsgi"]
