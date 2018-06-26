FROM python:3.4-alpine

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

RUN node --version
RUN npm --version

RUN npm install -g babel-cli
RUN npm install -g sass
RUN npm install -g yarn

WORKDIR /app
RUN pip install -r requirements.txt
RUN yarn

EXPOSE 5000

CMD ["python", "app.py"]
