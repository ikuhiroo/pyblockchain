import hashlib
import json
import logging
import sys
import time
import utils

# コンソール上にもログを出力する
logging.basicConfig(level=logging.INFO, stream=sys.stdout)


class BlockChain(object):
    # blockchainクラスの作成
    def __init__(self):
        self.transaction_pool = []
        self.chain = []
        # 初期値
        self.create_block(0, self.hash({}))

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


def pprint(chains):
    # 出力形式
    for i, chain in enumerate(chains):
        print(f'{"="*25} Chain {i} {"="*25}')
        # kとvの幅を揃える
        for k, v in chain.items():
            if k == "transaction":
                print(k)
                for d in v:
                    print(f'{"-"}*40')
                    for kk, vv in d.items():
                        print(f'{kk:30}{vv}')
            else:
                print(f'{k:15}{v}')
    print(f'{"*"*25}')


if __name__ == "__main__":
    import doctest
    doctest.testmod()

    block_chain = BlockChain()
    pprint(block_chain.chain)

    block_chain.add_transaction("A", "B", 1.0)
    previous_hash = block_chain.hash(block_chain.chain[-1])
    block_chain.create_block(5, previous_hash)
    pprint(block_chain.chain)

    block_chain.add_transaction("C", "D", 2.0)
    block_chain.add_transaction("X", "Y", 3.0)
    previous_hash = block_chain.hash(block_chain.chain[-1])
    block_chain.create_block(2, previous_hash)
    pprint(block_chain.chain)
