from ecdsa import NIST256p
from ecdsa import SigningKey


class Wallet(object):
    def __init__(self):
        # generate private_key (unknown) by NIST256p curve
        self._private_key = SigningKey.generate(curve=NIST256p)
        # generate public_key (unknown) by private_key
        self._public_key = self._private_key.get_verifying_key()

    @property  # getter
    def private_key(self):
        return self._private_key.to_string().hex()

    @property  # getter
    def public_key(self):
        return self._public_key.to_string().hex()


if __name__ == "__main__":
    wallet = Wallet()
    # メソッドとは異なり()は不要
    print(wallet.private_key)
    print(wallet.public_key)
