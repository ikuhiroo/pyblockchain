import hashlib
import json
import logging
import sys
import time
import utils

MININIG_DIFFICULTY = 3
MININIG_SENDER = "THE BLOCKCHAIN"
MININIG_REWARD = 1.0

# コンソール上にもログを出力する
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
# loggingではなくてloggerにする
# 後ほどmojuleとし用いるため（topでは使わない）
logger = logging.getLogger(__name__)


class BlockChain(object):
    # blockchainクラスの作成
    def __init__(self, blockchain_address=None):
        self.transaction_pool = []
        self.chain = []
        # 初期値
        self.create_block(0, self.hash({}))
        self.blockchain_address = blockchain_address

    # blockの作成
    def create_block(self, nonce, previous_hash):
        block = utils.sorted_dict_by_key({
            "timestamp": time.time(),
            "transaction": self.transaction_pool,
            "nonce": nonce,
            "previous_hash": previous_hash
        })
        self.chain.append(block)
        self.transaction_pool = []
        return block

    def hash(self, block):
        """ SHA-256 hash generator by double-check (sorted json dumps)
        >>> block = {"b": 2, "a": 1}
        >>> block2 = {"a": 1, "b": 2}
        >>> print(json.dumps(block, sort_keys=True))
        {"a": 1, "b": 2}
        >>> print(json.dumps(block2, sort_keys=True))
        {"a": 1, "b": 2}
        """
        sorted_block = json.dumps(block, sort_keys=True)
        return hashlib.sha256(sorted_block.encode()).hexdigest()

    def add_transaction(self, sender_blockchain_address, recipient_blockchain_address, value):
        """ create transaction"""
        transaction = utils.sorted_dict_by_key({
            "sender_blockchain_address": sender_blockchain_address,
            "recipient_blockchain_address": recipient_blockchain_address,
            "value": float(value)
        })
        self.transaction_pool.append(transaction)
        return True

    def valid_proof(self, transactions, previous_hash, nonce, difficulty=MININIG_DIFFICULTY):
        # nonceを計算する
        guess_block = utils.sorted_dict_by_key({
            "transactions": transactions,
            "nonce": nonce,
            "previous_hash": previous_hash
        })
        guess_hash = self.hash(guess_block)
        return guess_hash[:difficulty] == "0" * difficulty

    def proof_of_work(self):
        # nonceを計算できるまで繰り返し計算を行う
        transactions = self.transaction_pool.copy()
        previous_hash = self.hash(self.chain[-1])
        nonce = 0
        while self.valid_proof(transactions, previous_hash, nonce) is False:
            nonce += 1
        return nonce

    def mining(self):
        self.add_transaction(
            sender_blockchain_address=MININIG_SENDER,
            recipient_blockchain_address=self.blockchain_address,
            value=MININIG_REWARD
        )
        nonce = self.proof_of_work()
        previous_hash = self.hash(self.chain[-1])
        self.create_block(nonce, previous_hash)
        # logサーチするのに良い記法
        logger.info({"action": "mining", "status": "success"})
        return True


if __name__ == "__main__":
    import doctest
    doctest.testmod()

    my_blockchain_address = "my_blockchain_address"
    block_chain = BlockChain(blockchain_address=my_blockchain_address)
    utils.pprint(block_chain.chain)

    block_chain.add_transaction("A", "B", 1.0)
    block_chain.mining()
    utils.pprint(block_chain.chain)

    block_chain.add_transaction("C", "D", 2.0)
    block_chain.add_transaction("X", "Y", 3.0)
    block_chain.mining()
    utils.pprint(block_chain.chain)
