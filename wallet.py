import base58
import codecs
import hashlib


from ecdsa import NIST256p
from ecdsa import SigningKey


class Wallet(object):
    def __init__(self):
        # generate private_key (unknown) by NIST256p curve
        self._private_key = SigningKey.generate(curve=NIST256p)
        # generate public_key (unknown) by private_key
        self._public_key = self._private_key.get_verifying_key()
        # generate blockchain_address
        self._blockchain_address = self.generate_blockchain_address()

    @property  # getter
    def private_key(self):
        return self._private_key.to_string().hex()

    @property  # getter
    def public_key(self):
        return self._public_key.to_string().hex()

    @property
    def blockchain_address(self):
        return self._blockchain_address

    def generate_blockchain_address(self):
        """
        blockchain_addressを作るための仕様
        """
        # 2. SHA-256 for the public key
        public_key_bytes = self._public_key.to_string()
        sha256_bpk = hashlib.sha256(public_key_bytes)
        sha256_bpk_digest = sha256_bpk.digest()

        # 3. Ripemd160 for the SHA-256
        ripemd160_bpk = hashlib.new("ripemd160")
        ripemd160_bpk.update(sha256_bpk_digest)
        ripemd160_bpk_digest = ripemd160_bpk.digest()
        ripemd160_bpk_hex = codecs.encode(ripemd160_bpk_digest, "hex")

        # 4. Add network byte
        network_byte = b"00"  # mainとtestに分けるとき，mainは00
        network_bitcoin_public_key = network_byte + ripemd160_bpk_hex
        network_bitcoin_public_key_bytes = codecs.decode(
            network_bitcoin_public_key, "hex")

        # 5. Double SHA-256
        sha256_bpk = hashlib.sha256(network_bitcoin_public_key_bytes)
        sha256_bpk_digest = sha256_bpk.digest()
        sha256_2_nbpk = hashlib.sha256(sha256_bpk_digest)
        sha256_2_nbpk_digest = sha256_2_nbpk.digest()
        sha256_hex = codecs.encode(sha256_2_nbpk_digest, "hex")

        # 6. Get checksum (データの信頼性を確かめる)
        checksum = sha256_hex[:8]

        # 7. Concatenate public key and checksum
        address_hex = (network_bitcoin_public_key + checksum).decode("utf-8")

        # 8. Encoding the key with Base58
        blockchain_address = base58.b58encode(address_hex).decode("utf-8")
        return blockchain_address


if __name__ == "__main__":
    wallet = Wallet()
    # メソッドとは異なり()は不要
    print(wallet.private_key)
    print(wallet.public_key)
    print(wallet.blockchain_address)
