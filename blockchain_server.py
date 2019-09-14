from flask import Flask
from flask import jsonify

import blockchain
import wallet

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "Hello, world!"


if __name__ == "__main__":
    # スクリプトを実行する場合のオプションを指定
    # オプションがない場合はdefault値が用いられる
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", default=5000,
                        type=int, help="port to listen on")

    args = parser.parse_args()
    port = args.port

    # 同時リクエストを引き受ける
    app.run(host="0.0.0.0", port=port, threaded=True, debug=True)
