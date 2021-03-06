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

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


class BlockChain(object):
    """
    blockchainを構成する機能

    Attributes
    ----------
    transaction_pool : list of dicts
        mining前にtransactionを追加する場所

    chain : list of dicts
        block chain

    neighbours : dict
        block chain serverとその情報

    blockchain_address : str
        wallet serverのアドレス

    port : int
        wallet serverのlistenしているポート
        複数サーバーの代わりにポートを複数開ける

    mining_semaphore : threading
        並列処理をするプロセスが1つだけ

    sync_neighbours_semaphore : threading
        付近のノードを同期させる
    """

    def __init__(self, blockchain_address=None, port=None):
        """
        blockchainを構成する機能

        Parameters
        ----------
        blockchain_address : int
            walletのblockchain_address

        port : int
            wallet serverのポート番号
        """
        self.transaction_pool = []
        self.chain = []
        self.neighbours = []
        self.create_block(0, self.hash({}))
        self.blockchain_address = blockchain_address
        self.port = port
        self.mining_semaphore = threading.Semaphore(1)
        self.sync_neighbours_semaphore = threading.Semaphore(1)

    def run(self):
        self.sync_neighbours()
        self.resolve_conflicts()
        self.start_mining()

    def set_neighbours(self):
        """
        条件に沿ったnodeを検索する．

        See Also
        ----------
        NEIGHBOURS_IP_RANGE_NUM : tuple
            NEIGHBOURS_IP_RANGE_NUM[0] : int
                start_ip_range
            NEIGHBOURS_IP_RANGE_NUM[1] : int
                end_ip_range

        BLOCKCHAIN_PORT_RANGE : tuple
            BLOCKCHAIN_PORT_RANGE[0] : int
                start_port
            BLOCKCHAIN_PORT_RANGE[1] : int
                end_port
        """
        self.neighbours = utils.find_neighbours(
            utils.get_host(), self.port,
            NEIGHBOURS_IP_RANGE_NUM[0], NEIGHBOURS_IP_RANGE_NUM[1],
            BLOCKCHAIN_PORT_RANGE[0], BLOCKCHAIN_PORT_RANGE[1])
        logger.info({
            "action": "set_neighbours",
            "neighbours": self.neighbours
        })

    def sync_neighbours(self):
        """
        set_neighboursを並列処理する
        BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SECごとにsync_neighbours()を呼び出す

        See Also
        ----------
        BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC : int
        """
        is_acquire = self.sync_neighbours_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.sync_neighbours_semaphore.release)
                self.set_neighbours()
                loop = threading.Timer(
                    BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC, self.sync_neighbours
                )
                loop.start()

    # blockの作成
    def create_block(self, nonce, previous_hash):
        """
        Blockを作成する

        Parameters
        ----------
        nonce: int

        previous_hash: str

        Returns
        -------
        block : dict

        See Also
        --------
        >>> block_chain = BlockChain()
        >>> block_1 = block_chain.create_block(5, "hash 1")
        >>> block_1['nonce']
        5
        >>> block_1['previous_hash']
        'hash 1'
        >>> block_2 = block_chain.create_block(2, "hash 2")
        >>> block_2['nonce']
        2
        >>> block_2['previous_hash']
        'hash 2'
        """
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
        """ 
        SHA-256 hash generator by double-check (sorted json dumps)

        Parameters
        ----------
        block: dict

        Returns
        -------
        hashlib.sha256(sorted_block.encode()).hexdigest() : str

        See Also
        --------
        >>> block_init = {}
        >>> hashlib.sha256(json.dumps(block_init, sort_keys=True).encode()).hexdigest()
        '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a'
        >>> block = {"b": 2, "a": 1}
        >>> block2 = {"a": 1, "b": 2}
        >>> print(json.dumps(block, sort_keys=True))
        {"a": 1, "b": 2}
        >>> print(json.dumps(block2, sort_keys=True))
        {"a": 1, "b": 2}
        >>> hashlib.sha256(json.dumps(block2, sort_keys=True).encode()).hexdigest()
        'd8497d9d82770a70729261095aa98f7ef5154d7af499f8037b6ca250296785a6'
        """
        sorted_block = json.dumps(block, sort_keys=True)
        return hashlib.sha256(sorted_block.encode()).hexdigest()

    def add_transaction(
        self, sender_blockchain_address, recipient_blockchain_address, value,
        sender_public_key=None, signature=None
    ):
        """
        transactionを追加する．
        ex. wallet A -> wallet B に 1.0送金．

        Parameters
        ----------
        sender_blockchain_address: str
            wallet Aのblockchain address

        recipient_blockchain_address: str
            wallet Bのblockchain address

        value: float
            1.0

        sender_public_key: str

        signature : str

        Returns
        -------
        bool

        See Also
        --------
        """
        transaction = utils.sorted_dict_by_key({
            "sender_blockchain_address": sender_blockchain_address,
            "recipient_blockchain_address": recipient_blockchain_address,
            "value": float(value)
        })
        # miningの場合
        if sender_blockchain_address == MINING_SENDER:
            self.transaction_pool.append(transaction)
            return True

        # mining以外の場合
        if self.verify_transaction_signature(
                sender_public_key, signature, transaction):

            # 送り金がない場合
            if self.calculate_total_amount(sender_blockchain_address) < float(value):
                logger.error(
                    {'action': 'add_transaction', 'error': 'no_value'})
                return False

            self.transaction_pool.append(transaction)
            return True
        return False

    def create_transaction(self, sender_blockchain_address,
                           recipient_blockchain_address, value,
                           sender_public_key, signature):
        """
        ・add_transaction + 同期
        ・miningの場合は同期はしない

        Parameters
        ----------
        sender_blockchain_address: str
            wallet Aのblockchain address

        recipient_blockchain_address: str
            wallet Bのblockchain address

        value: float
            1.0

        sender_public_key : str

        signature : str
        
        Returns
        -------
        is_transacted : bool

        See Also
        --------
        """

        # transactionが追加されたかどうか
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
        """
        transactionの証明を行う

        公開鍵とsignatureとtransactionsから証明する
        1. message: transactionsをSHA-256でハッシュ化（bytes）し，16進数文字列化
        2. signature_bytes: signatureをbytes化
        3. verifying_key: sender_public_keyから生成する

        Parameters
        ----------
        sender_public_key: str

        signature: str

        transaction: list in dict

        Returns
        -------
        verified_Key : str

        See Also
        --------
        """
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
        """
        nonceを計算する．

        Parameters
        ----------
        transactions: list of dicts
            [{"recipient_blockchain_address": str, "sender_blockchain_address": str, "value": float}]

        previous_hash: str
            hash化（[{"nonce": int, "previous_hash": str, "timestamp": float, "transactions": list}]）

        nonce: int
            サーチ対象

        difficulty: int
            miningの難易度．hash化した文字列の先頭"0"の連続数

        Returns
        -------
        bool

        See Also
        --------
        """
        guess_block = utils.sorted_dict_by_key({
            "transactions": transactions,
            "nonce": nonce,
            "previous_hash": previous_hash
        })
        guess_hash = self.hash(guess_block)
        return guess_hash[:difficulty] == "0" * difficulty

    def proof_of_work(self):
        """
        nonceを計算できるまで繰り返し計算を行う

        See Also
        --------
        """
        transactions = self.transaction_pool.copy()
        previous_hash = self.hash(self.chain[-1])
        nonce = 0
        while self.valid_proof(transactions, previous_hash, nonce) is False:
            nonce += 1
        return nonce

    def mining(self):
        """
        miningをし，blockを生成する．
        transactionが空の場合もminingを行う．

        See Also
        --------
        >>> block_chain = BlockChain()
        >>> my_blockchain_address = "my_blockchain_address"
        >>> block_chain = BlockChain(blockchain_address=my_blockchain_address)        
        >>> block_init = {}
        >>> previous_hash = hashlib.sha256(json.dumps(block_init, sort_keys=True).encode()).hexdigest()
        >>> block_chain.chain = [{"nonce": 0, "previous_hash": previous_hash, "timestamp": 1568623709.059293, "transactions": []}]
        >>> block_chain.transaction_pool = [{"recipient_blockchain_address": "A", "sender_blockchain_address": "B", "value": 1.0}]
        >>> nonce = block_chain.proof_of_work()
        >>> nonce
        8636
        >>> previous_hash = block_chain.hash(block_chain.chain[-1])
        >>> guess_block = utils.sorted_dict_by_key({"transactions": block_chain.transaction_pool, "nonce": nonce, "previous_hash": previous_hash})
        >>> block_chain.hash(guess_block)
        '000494115f84a2b4e5526c65fe44364405f4af36e119ac75e1414f7da2f8f673'
        """
        # 空のtransactionの時はマイニングにしないようにする
        # if not self.transaction_pool:
        #     return False

        self.add_transaction(
            sender_blockchain_address=MINING_SENDER,
            recipient_blockchain_address=self.blockchain_address,
            value=MINING_REWARD
        )
        nonce = self.proof_of_work()
        previous_hash = self.hash(self.chain[-1])
        self.create_block(nonce, previous_hash)

        # logサーチするのに良い記法
        logger.info({
            "action": "mining",
            "status": "success"
        })

        # 最も長いchainを採用
        for node in self.neighbours:
            requests.put(f'http://{node}/consensus')

        return True

    def start_mining(self):
        """
        MINING_TIMER_SECごとにself-mining（start_mining）を行う

        ・blocking=Trueにすると待ち行列になる
        ・ExitStackを使うと，callbackが明示的に記述できて、必ず実行したい処理が一目見てわかる。

        See Also
        --------
        threading.Semaphore(1) : self-miningは1つだけ
        MINING_TIMER_SEC : 擬似的にマイニングの時間を設定
        """
        is_acquire = self.mining_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.mining_semaphore.release)
                self.mining()
                loop = threading.Timer(MINING_TIMER_SEC, self.start_mining)
                loop.start()

    def calculate_total_amount(self, blockchain_address):
        """
        walletのビットコインを計算する．
        ex. 
        MINING_SENDER -> my_blockchain_address 10.0
        my_blockchain_address -> A 5.0
        MINING_SENDER -> my_blockchain_address 1.0

        Parameters
        ----------
        blockchain_address: str

        See Also
        --------
        >>> block_chain = BlockChain()
        >>> my_blockchain_address = "my_blockchain_address"
        >>> block_chain = BlockChain(blockchain_address=my_blockchain_address)
        >>> block_chain.transaction_pool = [{"recipient_blockchain_address": my_blockchain_address, "sender_blockchain_address": MINING_SENDER, "value": 10.0}]
        >>> block_chain.transaction_pool.append({"recipient_blockchain_address": "A", "sender_blockchain_address": my_blockchain_address, "value": 5.0})
        >>> previous_hash = block_chain.hash(block_chain.chain[-1])
        >>> nonce = block_chain.proof_of_work()
        >>> _ = block_chain.create_block(nonce, previous_hash)
        >>> block_chain.mining()
        True
        >>> print(block_chain.calculate_total_amount(my_blockchain_address))
        6.0
        >>> print(block_chain.calculate_total_amount("Y"))
        0.0
        """
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
        """
        blockのvalidation check

        Parameters
        ----------
        chain: list in dict

        See Also
        --------
        """
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
        """
        Consensus
        最も長いchainを採用する

        See Also
        --------
        """
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


if __name__ == "__main__":
    import doctest
    doctest.testmod()

    # block_chain = BlockChain()
    # my_blockchain_address = "my_blockchain_address"
    # block_chain = BlockChain(blockchain_address=my_blockchain_address)
    # utils.pprint(block_chain.chain)

    # block_chain.add_transaction(MINING_SENDER, my_blockchain_address, 2.0)
    # block_chain.add_transaction(MINING_SENDER, "A", 3.0)
    # previous_hash = block_chain.hash(block_chain.chain[-1])
    # nonce = block_chain.proof_of_work()
    # block_chain.create_block(nonce, previous_hash)
    # block_chain.mining()
    # utils.pprint(block_chain.chain)

    # print("my", block_chain.calculate_total_amount(my_blockchain_address))
    # print("A", block_chain.calculate_total_amount("A"))
