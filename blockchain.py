import logging
import sys
import time

# コンソール上にもログを出力する
logging.basicConfig(level=logging.INFO, stream=sys.stdout)


class BlockChain(object):
    # blockchainクラスの作成
    def __init__(self):
        self.transaction_pool = []
        self.chain = []
        # 初期値
        self.create_block(0, "init hash")

    # blockの作成
    def create_block(self, nonce, previous_hash):
        block = {
            "timestamp": time.time(),
            "transaction": self.transaction_pool,
            "nonce": nonce,
            "previous_hash": previous_hash
        }
        self.chain.append(block)
        self.transaction_pool = []
        return block

# 出力形式
def pprint(chains):
    for i, chain in enumerate(chains):
        print(f'{"="*25} Chain {i} {"="*25}')
        # kとvの幅を揃える
        for k, v in chain.items():
            print(f'{k:15}{v}')
    print(f'{"*"*25}')


if __name__ == "__main__":
    block_chain = BlockChain()
    pprint(block_chain.chain)
    block_chain.create_block(5, "hash 1")
    pprint(block_chain.chain)
    block_chain.create_block(2, "hash 2")
    pprint(block_chain.chain)
