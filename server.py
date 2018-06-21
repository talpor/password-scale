from botocore.exceptions import ClientError
from flask import Flask, request, abort

from contrib.crypto import generate_key, encrypt, decrypt
from contrib.onetimesecret import OneTimeCli

import boto3
import os
import re
import requests
import time

server = Flask(__name__)

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
ENCRYPTION_KEY_URL = os.environ.get(
    'ENCRYPTION_KEY_URL',
    'https://scale.talpor.com/public_key'
)
ONETIMESECRET_KEY = os.environ.get('ONETIMESECRET_KEY')
ONETIMESECRET_USER = os.environ.get('ONETIMESECRET_USER')
PASSWORD_STORAGE = os.environ.get('PASSWORD_STORAGE')
AWS_S3_REGION = os.environ.get('AWS_S3_REGION', 'us-east-1')

secret_key = generate_key(os.environ.get('SECRET_KEY'))
private_key = secret_key.exportKey("PEM")
public_key = secret_key.publickey().exportKey("PEM")

s3 = boto3.client(
    's3',
    region_name=AWS_S3_REGION,
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
                raise Exception('Unable to retrieve {} from {}'.format(
                    key, ENCRYPTION_KEY_URL))
            s3.put_object(Bucket=bucket, Body=str.encode(r.text), Key=key)
            return r.text
        else:
            raise e
    return response['Body'].read()


def _save_backup_copy(bucket, channel, key):
    path = key.split('/')
    file = path.pop()
    route = '/'.join(path) + '/' if path else ''
    new_key = '{}/{}.{}.{}'.format(channel, route, file, int(time.time()))
    try:
        s3.copy_object(
            Bucket=bucket,
            CopySource='{}/{}/{}'.format(bucket, channel, key),
            Key=new_key)
    except ClientError as e:
        if e.response['Error']['Code'] in ['NoSuchKey', 'NoSuchBucket']:
            return False
        else:
            raise e
    return True


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
    output = ''
    try:
        bucket = s3.list_objects(Bucket=PASSWORD_STORAGE, Prefix=prefix)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            s3.create_bucket(Bucket=PASSWORD_STORAGE)
        else:
            raise e
    else:
        if 'Contents' in bucket:
            output = '\n'.join([
                x['Key'] for x in bucket['Contents']
                if not re.match('.+\/\.\w+', x['Key'])
            ])

    encryption_key = _get_encryption_key()
    return encrypt(output, encryption_key)


@server.route('/insert', methods=['POST'])
def insert():
    bucket = PASSWORD_STORAGE
    kargs = {
        'Bucket': bucket,
        'Body': str.encode(request.form['secret']),  # already encrypted
        'Key': request.form['path']
    }
    try:
        _save_backup_copy(bucket, *request.form['path'].split('/', 1))
        s3.put_object(**kargs)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            s3.create_bucket(Bucket=bucket)
            s3.put_object(**kargs)
        else:
            raise e
    return 'ok'


@server.route('/remove', methods=['POST'])
def remove():
    channel = request.form['channel']
    app = request.form['app']
    bucket = PASSWORD_STORAGE

    if not _save_backup_copy(bucket, channel, app):
        abort(403)

    s3.delete_object(Bucket=bucket, Key='{}/{}'.format(channel, app))
    return 'ok'


if __name__ == '__main__':
    server.run(host='0.0.0.0', port=8090)
