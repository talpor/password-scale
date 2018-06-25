FROM python:3.4-alpine
ADD . /app
WORKDIR /app
RUN apk update
RUN apk add git gcc g++ make python-dev postgresql-dev libffi-dev libressl-dev
RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
