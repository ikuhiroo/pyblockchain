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


def pprint(chains):
    # 出力形式
    for i, chain in enumerate(chains):
        print(f'{"="*25} Chain {i} {"="*25}')
        # kとvの幅を揃える
        for k, v in chain.items():
            print(f'{k:15}{v}')
    print(f'{"*"*25}')


if __name__ == "__main__":
    import doctest
    doctest.testmod()

    block_chain = BlockChain()
    pprint(block_chain.chain)

    previous_hash = block_chain.hash(block_chain.chain[-1])
    block_chain.create_block(5, previous_hash)
    pprint(block_chain.chain)

    previous_hash = block_chain.hash(block_chain.chain[-1])
    block_chain.create_block(2, previous_hash)
    pprint(block_chain.chain)
