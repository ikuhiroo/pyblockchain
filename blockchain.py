import contextlib
import hashlib
import json
import logging
import sys
import time
import threading
import requests

from ecdsa import NIST256p
from ecdsa import VerifyingKey

import utils

MINING_DIFFICULTY = 3
MINING_SENDER = "THE BLOCKCHAIN"
MINING_REWARD = 1.0
MINING_TIMER_SEC = 20

BLOCKCHAIN_PORT_RANGE = (5000, 5003)
NEIGHBOURS_IP_RANGE_NUM = (0, 1)
BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC = 20

# コンソール上にもログを出力する
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
# loggingではなくてloggerにする
# 後ほどmojuleとし用いるため（topでは使わない）
logger = logging.getLogger(__name__)


class BlockChain(object):
    # blockchainクラスの作成
    def __init__(self, blockchain_address=None, port=None):
        self.transaction_pool = []
        self.chain = []
        # 初期値
        self.neighbours = []
        self.create_block(0, self.hash({}))
        self.blockchain_address = blockchain_address
        # 複数サーバーの代わりにポートを複数開ける
        self.port = port
        # 並列処理をするプロセスが1つだけ
        self.mining_semaphore = threading.Semaphore(1)
        # 付近のノードを同期させる
        self.sync_neighbours_semaphore = threading.Semaphore(1)

    def run(self):
        self.sync_neighbours()
        self.resolve_conflicts()
        # self.start_mining()
    
    def set_neighbours(self):
        self.neighbours = utils.find_neighbours(
            utils.get_host(), self.port,
            NEIGHBOURS_IP_RANGE_NUM[0], NEIGHBOURS_IP_RANGE_NUM[1],
            BLOCKCHAIN_PORT_RANGE[0], BLOCKCHAIN_PORT_RANGE[1])
        logger.info({"action": "set_neighbours",
                     "neighbours": self.neighbours})

    def sync_neighbours(self):
        "set_neighboursをBLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SECごとに呼び出す"
        is_acquire = self.sync_neighbours_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.sync_neighbours_semaphore.release)
                self.set_neighbours()
                loop = threading.Timer(
                    BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC, self.sync_neighbours)
                loop.start()

    # blockの作成
    def create_block(self, nonce, previous_hash):
        block = utils.sorted_dict_by_key({
            "timestamp": time.time(),
            "transactions": self.transaction_pool,
            "nonce": nonce,
            "previous_hash": previous_hash
        })
        self.chain.append(block)
        self.transaction_pool = []

        # 同期させる
        for node in self.neighbours:
            requests.delete(f"http://{node}/transactions")

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

    def add_transaction(
        self, sender_blockchain_address, recipient_blockchain_address, value,
        sender_public_key=None, signature=None
    ):
        """ create transaction"""
        transaction = utils.sorted_dict_by_key({
            "sender_blockchain_address": sender_blockchain_address,
            "recipient_blockchain_address": recipient_blockchain_address,
            "value": float(value)
        })
        # miningのsenderの場合はverifyなし
        if sender_blockchain_address == MINING_SENDER:
            self.transaction_pool.append(transaction)
            return True

        # verifyしてokなら
        if self.verify_transaction_signature(
                sender_public_key, signature, transaction):
            # 送り金がない場合
            # if self.calculate_total_amount(sender_blockchain_address) < float(value):
            #     logger.error(
            #         {'action': 'add_transaction', 'error': 'no_value'})
            #     return False
            self.transaction_pool.append(transaction)
            return True
        return False

    # add_transactionと同じ内容だが
    # 他のノードに同期させたい
    # miningの場合は同期はしない
    def create_transaction(self, sender_blockchain_address,
                           recipient_blockchain_address, value,
                           sender_public_key, signature):

        is_transacted = self.add_transaction(
            sender_blockchain_address, recipient_blockchain_address,
            value, sender_public_key, signature)

        # 同期
        if is_transacted:
            for node in self.neighbours:
                requests.put(
                    f"http://{node}/transactions",
                    json={
                        "sender_blockchain_address": sender_blockchain_address,
                        "recipient_blockchain_address": recipient_blockchain_address,
                        "value": value,
                        "sender_public_key": sender_public_key,
                        "signature": signature,
                    }
                )

        return is_transacted

    def verify_transaction_signature(
            self, sender_public_key, signature, transaction):
        sha256 = hashlib.sha256()
        sha256.update(str(transaction).encode("utf-8"))
        message = sha256.digest()
        signature_bytes = bytes().fromhex(signature)
        verifying_key = VerifyingKey.from_string(
            bytes().fromhex(sender_public_key), curve=NIST256p
        )
        verified_Key = verifying_key.verify(signature_bytes, message)
        return verified_Key

    def valid_proof(self, transactions, previous_hash, nonce, difficulty=MINING_DIFFICULTY):
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
        # 空のtransactionの時はマイニングにしないようにする
        if not self.transaction_pool:
            return False

        self.add_transaction(
            sender_blockchain_address=MINING_SENDER,
            recipient_blockchain_address=self.blockchain_address,
            value=MINING_REWARD
        )
        nonce = self.proof_of_work()
        previous_hash = self.hash(self.chain[-1])
        self.create_block(nonce, previous_hash)
        # logサーチするのに良い記法
        logger.info({"action": "mining", "status": "success"})

        # 最も長いchainを採用
        for node in self.neighbours:
            requests.put(f'http://{node}/consensus')

        return True

    def start_mining(self):
        # blocking=Trueにすると待ち行列になる
        # self-miningは1つだけ
        is_acquire = self.mining_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.mining_semaphore.release)
                self.mining()
                # 擬似的にマイニングの時間を設定
                loop = threading.Timer(MINING_TIMER_SEC, self.start_mining)
                loop.start()

    def calculate_total_amount(self, blockchain_address):
        total_amount = 0.0
        for block in self.chain:
            for transaction in block["transactions"]:
                value = float(transaction["value"])
                if blockchain_address == transaction["recipient_blockchain_address"]:
                    total_amount += value
                if blockchain_address == transaction["sender_blockchain_address"]:
                    total_amount -= value
        return total_amount

    def valid_chain(self, chain):
        pre_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            # blockが正しいかどうか
            if block["previous_hash"] != self.hash(pre_block):
                return False

            # 正しいnanceかどうか
            if not self.valid_proof(
                    block["transactions"], block["previous_hash"],
                    block["nonce"], MINING_DIFFICULTY):
                return False

            pre_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        "Consensus"
        longest_chain = None
        max_length = len(self.chain)
        for node in self.neighbours:
            response = requests.get(f"http://{node}/chain")
            if response.status_code == 200:
                response_json = response.json()
                chain = response_json["chain"]
                chain_length = len(chain)
                if chain_length > max_length and self.valid_chain(chain):
                    max_length = chain_length
                    longest_chain = chain

        if longest_chain:
            self.chain = longest_chain
            logger.info({"action": "resolve_conflicts", "status": "replaced"})
            return True

        logger.info({"action": "resolve_conflicts", "status": "not_replaced"})
        return False
