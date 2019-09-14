from flask import Flask
from flask import jsonify

import blockchain
import wallet

app = Flask(__name__)

cache = {}


def get_blockchain():
    # blockchainの情報は本来DBに入れる
    # 今回はglobalにchcheに入れる
    # すぐに呼び出せるようにする
    cached_blockchain = cache.get("blockchain")
    # １度しか呼ばれない
    if not cached_blockchain:
        miners_wallet = wallet.Wallet()
        cache["blockchain"] = blockchain.BlockChain(
            blockchain_address=miners_wallet.blockchain_address,
            port=app.config["port"]
        )
        app.logger.warning({
            "private_key": miners_wallet.private_key,
            "public_key": miners_wallet.public_key,
            "blockchain_address": miners_wallet.blockchain_address
        })
    return cache["blockchain"]


@app.route('/chain', methods=['GET'])
def get_chain():
    block_chain = get_blockchain()
    response = {
        'chain': block_chain.chain
    }
    return jsonify(response), 200


if __name__ == "__main__":
    # スクリプトを実行する場合のオプションを指定
    # オプションがない場合はdefault値が用いられる
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", default=5000,
                        type=int, help="port to listen on")

    args = parser.parse_args()
    port = args.port

    app.config["port"] = port

    # 同時リクエストを引き受ける
    app.run(host="0.0.0.0", port=port, threaded=True, debug=True)
