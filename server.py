from botocore.exceptions import ClientError
from flask import Flask, request, abort

from contrib.crypto import generate_key, encrypt, decrypt
from contrib.onetimesecret import OneTimeCli

import boto3
import os
import requests

server = Flask(__name__)

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
ENCRYPTION_KEY_URL = os.environ.get('ENCRYPTION_KEY_URL')
ONETIMESECRET_KEY = os.environ.get('ONETIMESECRET_KEY')
ONETIMESECRET_USER = os.environ.get('ONETIMESECRET_USER')
PASSWORD_STORAGE = os.environ.get('PASSWORD_STORAGE')

secret_key = generate_key(os.environ.get('SECRET_KEY'))
private_key = secret_key.exportKey("PEM")
public_key = secret_key.publickey().exportKey("PEM")

s3 = boto3.client(
    's3',
    region_name='us-west-2',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)


def _get_encryption_key():
    bucket = PASSWORD_STORAGE
    key = 'password.scale.id_rsa.pub'
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            r = requests.get(ENCRYPTION_KEY_URL)
            if r.status_code != requests.codes.ok:
                raise Exception('Unable to retrieve {}'.format(key))
            s3.put_object(Bucket=bucket, Body=str.encode(r.text), Key=key)
            return r.text
        else:
            raise e
    return response['Body'].read()


@server.route('/public_key', methods=['GET'])
def get_public_key():
    return public_key


@server.route('/onetime_link', methods=['POST'])
def get_onetime_link():
    cli = OneTimeCli(ONETIMESECRET_USER, ONETIMESECRET_KEY)
    try:
        response = s3.get_object(
            Bucket=PASSWORD_STORAGE,
            Key=request.form['secret']
        )
    except ClientError as e:
        if e.response['Error']['Code'] in ['NoSuchKey', 'NoSuchBucket']:
            abort(404)
        else:
            raise e

    secret = decrypt(response['Body'].read(), private_key)
    encryption_key = _get_encryption_key()
    return encrypt(cli.create_link(secret), encryption_key)


@server.route('/list/<prefix>', methods=['POST'])
def list(prefix):
    try:
        bucket = s3.list_objects(Bucket=PASSWORD_STORAGE, Prefix=prefix)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            s3.create_bucket(Bucket=PASSWORD_STORAGE)
            output = '<empty>'
        else:
            raise e
    else:
        if 'Contents' in bucket:
            output = '\n'.join([x['Key'] for x in bucket['Contents']])
        else:
            output = '<empty>'

    encryption_key = _get_encryption_key()
    return encrypt(output, encryption_key)


@server.route('/insert', methods=['POST'])
def insert():
    kargs = {
        'Bucket': PASSWORD_STORAGE,
        'Body': str.encode(request.form['secret']),  # already encrypted
        'Key': request.form['path']
    }
    try:
        s3.put_object(**kargs)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            s3.create_bucket(Bucket=PASSWORD_STORAGE)
            s3.put_object(**kargs)
        else:
            raise e
    return 'ok'


if __name__ == '__main__':
    server.run(host='0.0.0.0', port=8090)
