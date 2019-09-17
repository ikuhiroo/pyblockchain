# pyblockchain

* node 1
```
$ python blockchain_server.py
```

* node 2
```
$ python blockchain_server.py  -p 5001
```

* node 3
```
$ python blockchain_server.py  -p 5002
```

* wallet A
```
python wallet_server.py
```

* wallet B
```
python wallet_server.py -p 8081 -g http://127.0.0.1:5001
```