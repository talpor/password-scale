# Password Scale

[![Build Status](https://travis-ci.org/talpor/password-scale.svg?branch=master)](https://travis-ci.org/talpor/password-scale)

Is a Slack command to manage shared passwords between the members of a channel in Slack.

This project was build focused in establishing a communication where the trustness between parties is not required, using the asymmetric algorithm RSA to share encrypted information point to point and where the only participant allowed to read the stored passwords is the _Password Server_, who is different and independent for each client.

## Commands

- `/pass` or `/pass list` list the available passwords in the channel.
- `/pass <secret>` or `/pass show <secret>` retrieve a one time use link with the secret content, this link expires in 15 minutes.
- `/pass insert <secret>` retrieve a link with an editor to create a secret, this link expires in 15 minutes.
- `/pass remove <secret>` make unreachable the secret, to complete deletion in necessary doing it manually from the s3 password storage.
- `/pass register <password_server_url>` this is the command used for the initial setup, it is only necessary to execute it once.

[![button](https://platform.slack-edge.com/img/add_to_slack.png)](https://slack.com/oauth/authorize?client_id=2554558892.385841792964&scope=commands)

## How it work?

Been _Alice_ and _Bob_ members of the same Slack group, they need to share the password of the service _"Bar"_. This is the process that they need to follow to share it. In this example _Alice_ will create the secret and _Bob_ will consult it.

### Creating a secret

- _**Alice:**_ Requests a link to create the secret (`/pass insert Bar`)
- *Proxy Server*: Generates an unique editor link, valid for 15 minutes
- *Slack:* Shows the editor link, only visible for Alice
- _**Alice:**_ Follows the link
- *Proxy Server:* Requests the the public key to the _Password Server_ and send it to the editor
- *Editor:* Displays itself in Alice's browser
- _**Alice:**_ Writes the shared secret
- _**Alice:**_ Press the "Create" button
- *Editor:* Encrypts the secret before sending the request
- *Editor:* Sends the request to the _Proxy Server_
- *Proxy Server:* Sends the encrypted secret to the _Password Server_ (note that this secret is indecipherable for this server)
- *Password Server:* Stores the encrypted secret in the configured S3 bucket.

**Note:** _Editor_ and _Proxy Server_ are the same server, but _Editor_ represents the frontend view.

### Retrieving a secret

- _**Bob:**_ Requests a link to see the secret (`/pass Bar` or `/pass show Bar`)
- *Proxy Server:* Requests the secret to the password server using the Slack team name and channel id
- *Password server:* Reads and decrypt the secret
- *Password server:* Generates one time use link with the secret, valid for 15 minutes (using One-Time Secret API)
- *Password server:* Encrypts the link with the _Proxy Server_ public key
- *Password server:* Sends the encrypted link to the _Proxy Server_
- *Proxy server:* Decrypts the one time use link
- *Proxy server:* Sends the link to Slack
- *Slack:* Shows the link only visible for Bob
- _**Bob**_: Follows the link
- *Onetimesecret*: Shows and destroys the secret

## How to deploy your own Password Server

In order to be efficient with the resource management and facilitate the deploy process this guide shows the process to put in producction a serverless infracstructure using AWS Lambda plus API Gateway using [Zappa](https://github.com/Miserlou/Zappa)

### Requirements

#### Required accounts
- AWS account (https://aws.amazon.com/)
- One-Time Secret account (https://onetimesecret.com/)

#### Installed software
- virtualenv + virtualenvwrapper (https://github.com/brainsik/virtualenv-burrito)
- python3

### Step-by-step guide

- Clone _password-scale_ project `git clone git@github.com:talpor/password-scale.git` and do `cd password-scale`
- Create a virtual environment `mkvirtualenv password-scale -p python3`
- Install dependencies `pip install -r requirements/storage-server.txt`
- Create _zappa_settings.json_ file based on _zappa_settings.example.json_ `cp zappa_settings.example.json zappa_settings.json`
- Modify _"s3_bucket"_ and _"environment_variables"_ variables in the new _zappa_settings.json_ file, replacing each value for your owns (for the _"environment_variables"_ see the table below)
- Deploy your server `zappa deploy`

Done! now you will need to register your server in Slack, using the command `/pass register <new_server_url>` to retrieve your server URL use the command `zappa status` and check the _API Gateway URL_. If you have any error using the command after configuration use `zappa tail` command to retrieve the server logs.

### Environment variables table

| Key | Description |
| --- | ----------- |
| AWS_ACCESS_KEY_ID | Your AWS public key, this key only needs permission to use S3 |
| AWS_SECRET_ACCESS_KEY | Your AWS private key |
| AWS_S3_REGION (optional) | The AWS region where the password storage bucket will be created, the default value is `us-east-1` |
| ENCRYPTION_KEY_URL (optional) | This is the url to retrieve the _Proxy Server_ public key, , the default value is `https://scale.talpor.com/public_key` |
| ONETIMESECRET_KEY | Your One-Time Secret API key |
| ONETIMESECRET_USER | Your One-Time Secret user name |
| PASSWORD_STORAGE | Unique name for your password storage bucket |
| BIP39 | Mnemonic code for generating deterministic keys, specification: https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki |
