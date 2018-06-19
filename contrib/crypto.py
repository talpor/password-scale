from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import HMAC
from Crypto.PublicKey import RSA
from struct import pack

import base64
import binascii


def encrypt(message, public_key):
    rsa_key = RSA.importKey(public_key)
    rsa_key = PKCS1_OAEP.new(rsa_key)
    return base64.b64encode(rsa_key.encrypt(str.encode(message)))


def decrypt(encrypted_message, private_key):
    rsakey = RSA.importKey(private_key)
    rsakey = PKCS1_OAEP.new(rsakey)
    try:
        return rsakey.decrypt(base64.b64decode(encrypted_message))
    except binascii.Error:
        return '<decrypting error>'


def generate_key(first_key):
    seed_128 = HMAC.new(
        bytes(first_key, 'utf-8') + b"Application: 2nd key derivation"
    ).digest()

    class PRNG(object):

        def __init__(self, seed):
            self.index = 0
            self.seed = seed
            self.buffer = b""

        def __call__(self, n):
            while len(self.buffer) < n:
                self.buffer += HMAC.new(
                    self.seed + pack("<I", self.index)).digest()
                self.index += 1
            result, self.buffer = self.buffer[:n], self.buffer[n:]
            return result

    return RSA.generate(2048, randfunc=PRNG(seed_128))
