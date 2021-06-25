BIP39 = "qwertyuiop"
from crypto import generate_key, encrypt, decrypt


def test_decrypt():
    secret_txt = "secret"
    secret_key = generate_key(BIP39)
    private_key = secret_key.exportKey("PEM")
    public_key = secret_key.publickey().exportKey("PEM")

    secret = encrypt(secret_txt, public_key)
    assert decrypt(secret, private_key) == bytes(secret_txt, 'utf-8')
