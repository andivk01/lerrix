from cryptography.fernet import Fernet
import base64, hashlib
import os

class DataKeeper:
    def __init__(self, filepath, enc_psw):
        self.enc_key = DataKeeper._gen_fernet_key(enc_psw)
        self.filepath = filepath

    def store(self, string):
        fer = Fernet(self.enc_key)
        with open(self.filepath, "wb") as file:
            file.write(fer.encrypt(string.encode()))
    def load(self):
        fer = Fernet(self.enc_key)
        if os.path.exists(self.filepath):
            with open(self.filepath, "rb") as file:
                return fer.decrypt(bytes(file.read())).decode()
        else:
            return None
    
    def _gen_fernet_key(passcode):
        hlib = hashlib.md5()
        hlib.update(passcode.encode())
        return base64.urlsafe_b64encode(hlib.hexdigest().encode('latin-1'))

