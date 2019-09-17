import base58
import codecs
import hashlib
import binascii

from ecdsa import NIST256p
from ecdsa import SigningKey

import utils


class Wallet(object):
    """
    walletを構成する機能

    Attributes
    ----------
    _private_key : 秘密鍵

    _public_key : 公開鍵

    _blockchain_address : ブロックチェーンアドレス

    """

    def __init__(self):
        """
        秘密鍵を作成する

        ECDSAを用いて楕円曲線から公開鍵となる値を計算する

        See Also
        --------
        """
        # generate private_key (unknown) by NIST256p curve
        self._private_key = SigningKey.generate(curve=NIST256p)
        # generate public_key (unknown) by private_key
        self._public_key = self._private_key.get_verifying_key()
        # generate blockchain_address
        self._blockchain_address = self.generate_blockchain_address()

    @property
    def private_key(self):
        """
        文字列にして16進数表示
        """
        return self._private_key.to_string().hex()

    @property
    def public_key(self):
        """
        文字列にして16進数表示
        """
        return self._public_key.to_string().hex()

    @property
    def blockchain_address(self):
        return self._blockchain_address

    def generate_blockchain_address(self):
        """
        blockchain_addressを作るための仕様

        1. ECDSAを用いて楕円曲線から公開鍵となる値を計算する
        2. 公開鍵をSHA-256でハッシュ化（bytes）
            sha256_bpk_digest: bytes
        3. ハッシュ値（SHA-256）をRipemd160でハッシュ化する
            ripemd160_bpk_hex（payload）: 16進数文字列
        4. プレフィックスとして16進数で"00"を先頭に加える
            network_bitcoin_public_key_bytes: bytes
        5. SHA-256で二重ハッシュ化
            sha256_hex: 16進数文字列
        6. checksum
            sha256_hexの前から8バイトをチェック
        7. 公開鍵とchecksumを組み合わせる
            address_hex: プレフィックス（SHA-256x2） + payload（SHA-256+Ripemd160）+ checksum（utf-8で文字列化）
        8. Base58（人が読みやすい値だけで形成された文字列にエンコード）でエンコード
            blockchain_address: utf-8

        See Also
        --------
        >>> wallet_A = Wallet()
        >>> public_key_bytes = wallet_A._public_key.to_string()
        >>> sha256_bpk = hashlib.sha256(public_key_bytes)
        >>> sha256_bpk_digest = sha256_bpk.digest()
        >>> sha256_bpk_hex = codecs.encode(sha256_bpk_digest, "hex")
        >>> ripemd160_bpk = hashlib.new("ripemd160")
        >>> ripemd160_bpk.update(sha256_bpk_digest)
        >>> ripemd160_bpk_digest = ripemd160_bpk.digest()
        >>> ripemd160_bpk_hex = codecs.encode(ripemd160_bpk_digest, "hex")
        >>> network_byte = b"00"
        >>> network_bitcoin_public_key = network_byte + ripemd160_bpk_hex
        >>> network_bitcoin_public_key_bytes = codecs.decode(network_bitcoin_public_key, "hex")
        >>> sha256_bpk = hashlib.sha256(network_bitcoin_public_key_bytes)
        >>> sha256_bpk_digest = sha256_bpk.digest()
        >>> sha256_2_nbpk = hashlib.sha256(sha256_bpk_digest)
        >>> sha256_2_nbpk_digest = sha256_2_nbpk.digest()
        >>> sha256_hex = codecs.encode(sha256_2_nbpk_digest, "hex")
        >>> checksum = sha256_hex[:8]
        >>> address_hex = (network_bitcoin_public_key + checksum).decode("utf-8")
        >>> blockchain_address = base58.b58encode(binascii.unhexlify(address_hex)).decode('utf-8')
        >>> blockchain_address = base58.b58encode(address_hex).decode("utf-8")
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
        network_byte = b"00"
        network_bitcoin_public_key = network_byte + ripemd160_bpk_hex
        network_bitcoin_public_key_bytes = codecs.decode(
            network_bitcoin_public_key, "hex")

        # 5. Double SHA-256
        sha256_bpk = hashlib.sha256(network_bitcoin_public_key_bytes)
        sha256_bpk_digest = sha256_bpk.digest()
        sha256_2_nbpk = hashlib.sha256(sha256_bpk_digest)
        sha256_2_nbpk_digest = sha256_2_nbpk.digest()
        sha256_hex = codecs.encode(sha256_2_nbpk_digest, "hex")

        # 6. Get checksum
        checksum = sha256_hex[:8]

        # 7. Concatenate public key and checksum
        address_hex = (network_bitcoin_public_key + checksum).decode("utf-8")

        # 8. Encoding the key with Base58
        # blockchain_address = base58.b58encode(address_hex).decode("utf-8")
        blockchain_address = base58.b58encode(
            binascii.unhexlify(address_hex)).decode('utf-8')
        return blockchain_address


class Transaction(object):
    """
    Transactionを構成する機能

    Attributes
    ----------
    sender_private_key : 

    sender_public_key : 

    sender_blockchain_address : 

    recipient_blockchain_address: 

    value: 

    """
    def __init__(self, sender_private_key, sender_public_key,
                 sender_blockchain_address, recipient_blockchain_address, value):
        self.sender_private_key = sender_private_key
        self.sender_public_key = sender_public_key
        self.sender_blockchain_address = sender_blockchain_address
        self.recipient_blockchain_address = recipient_blockchain_address
        self.value = value

    def generate_signature(self):
        """
        署名を生成する
        ex. wallet A -> wallet B に 1.0送金．
        sender_blockchain_address: wallet Aのblockchain_address
        recipient_blockchain_address: wallet Bのblockchain_address
        value: 1.0

        秘密鍵とtransactionsからsignatureを生成する
        1. transactionsをSHA-256でハッシュ化（bytes）
        2. message: ハッシュ化したtransactionsを16進数文字列化
        3. NIST256pでprivate_keyを作成（bytes）

        See Also
        --------
        >>> wallet_A = Wallet()
        >>> wallet_B = Wallet()
        >>> t = Transaction(wallet_A.private_key, wallet_A.public_key, wallet_A.blockchain_address, wallet_B.blockchain_address, 1.0)
        >>> _ = t.generate_signature()
        """
        sha256 = hashlib.sha256()
        transaction = utils.sorted_dict_by_key({
            "sender_blockchain_address": self.sender_blockchain_address,
            "recipient_blockchain_address": self.recipient_blockchain_address,
            "value": float(self.value)
        })
        # sha256のupdate
        sha256.update(str(transaction).encode("utf-8"))
        # hashのメッセージ
        message = sha256.digest()
        # private_keyの作成
        private_key = SigningKey.from_string(
            bytes().fromhex(self.sender_private_key), curve=NIST256p
        )
        # signアルゴリズム
        private_key_sign = private_key.sign(message)
        signature = private_key_sign.hex()
        return signature


if __name__ == "__main__":
    import doctest
    doctest.testmod()

    # wallet_M = Wallet()
    # wallet_A = Wallet()
    # wallet_B = Wallet()
    # t = Transaction(
    #     wallet_A.private_key, wallet_A.public_key, wallet_A.blockchain_address,
    #     wallet_B.blockchain_address, 1.0
    # )

    # # Blockchain Node (本来はRestなどで投げる)
    # import blockchain
    # block_chain = blockchain.BlockChain(
    #     blockchain_address=wallet_M.blockchain_address)
    # is_added = block_chain.add_transaction(
    #     wallet_A.blockchain_address,
    #     wallet_B.blockchain_address,
    #     1.0,
    #     wallet_A.public_key,
    #     t.generate_signature()
    # )
    # print("Added?", is_added)
    # block_chain.mining()
    # utils.pprint(block_chain.chain)

    # print("A", block_chain.calculate_total_amount(wallet_A.blockchain_address))
    # print("B", block_chain.calculate_total_amount(wallet_B.blockchain_address))