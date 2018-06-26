FROM python:3.6-alpine

COPY . /app

RUN apk update
RUN apk add \
    g++ \
    gcc \
    libressl-dev \
    make \
    nodejs \
    postgresql-dev \
    python-dev

RUN npm install -g yarn
RUN yarn global add babel-cli
RUN yarn global add node-sass

WORKDIR /app
RUN pip install -r requirements.txt
RUN yarn

EXPOSE 5000

CMD ["python", "app.py"]
