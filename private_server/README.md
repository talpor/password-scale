# Password Scale - Private Server

## How to deploy a private server

In order to be efficient with the resource management and facilitate the deploy process this guide shows the process to put in producction a serverless infracstructure using AWS Lambda plus API Gateway using [Zappa](https://github.com/Miserlou/Zappa)

### Requirements

#### Required accounts
- AWS account (https://aws.amazon.com/)
- One-Time Secret account (https://onetimesecret.com/)

#### Installed software
- pipenv

### Step-by-step guide

- Clone _password-scale_ project `git clone git@github.com:talpor/password-scale.git` and do `cd password-scale`
- Install requirements `pipenv sync`
- Create _zappa_settings.json_ file based on _zappa_settings.example.json_ `cp zappa_settings.example.json zappa_settings.json`
- Modify _"s3_bucket"_ and _"environment_variables"_ variables in the new _zappa_settings.json_ file, replacing each value for your owns (for the _"environment_variables"_ see the table below)
- Deploy your server `zappa deploy`

Done! now you will need to register your server in Slack, using the command `/pass register <new_server_url>` to retrieve your server URL use the command `zappa status` and check the _API Gateway URL_. If you have any error using the command after configuration use `zappa tail` command to check the server logs.

### Environment variables table

| Key | Description |
| --- | ----------- |
| AWS_ACCESS_KEY_ID | Your AWS public key, this key only needs permission to use S3 |
| AWS_SECRET_ACCESS_KEY | Your AWS private key |
| AWS_S3_REGION (optional) | The AWS region where the password storage bucket will be created, the default value is `us-east-1` |
| ENCRYPTION_KEY_URL (optional) | This is the url to retrieve the _Proxy Server_ public key, the default value is `https://scale.talpor.com/public_key` |
| ONETIMESECRET_KEY | Your One-Time Secret API key |
| ONETIMESECRET_USER | Your One-Time Secret user name |
| PASSWORD_STORAGE | Unique name for your password storage bucket |
| BIP39 | Mnemonic code for generating deterministic keys, specification: https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki |
