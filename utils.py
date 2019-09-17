import hashlib
import collections
import logging
import re
import socket

logger = logging.getLogger(__name__)

RE_IP = re.compile(
    "(?P<prefix_host>^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.)(?P<last_ip>\\d{1,3}$)")


def sorted_dict_by_key(unsorted_dict):
    """
    sorted by key

    Parameters
    ----------
    unsorted_dict : dict

    Returns
    -------
    collections.OrderedDict

    See Also
    --------
    >>> block = {"b": 2, "a": 1}
    >>> block2 = {"a": 1, "b": 2}
    >>> print(hashlib.sha256(str(block).encode()).hexdigest())
    46e391c4281c162dc452a58d0a756ec6568ebe3acbd9d3731d1eccc66c23d17b
    >>> print(hashlib.sha256(str(block2).encode()).hexdigest())
    3dffaea891e5dbadb390da33bad65f509dd667779330e2720df8165a253462b8
    >>> print(hashlib.sha256(str(sorted_dict_by_key(block)).encode()).hexdigest())
    3319a4f151023578ff06b0aa1838ee7ab82082fd6e43c2274ff0713f1ed23d53
    >>> print(hashlib.sha256(str(sorted_dict_by_key(block2)).encode()).hexdigest())
    3319a4f151023578ff06b0aa1838ee7ab82082fd6e43c2274ff0713f1ed23d53
    """
    return collections.OrderedDict(sorted(unsorted_dict.items(), key=lambda d: d[0]))


def pprint(chains):
    """
    出力形式

    Parameters
    ----------
    chains : list in dict

    See Also
    --------
    """
    for i, chain in enumerate(chains):
        print(f'{"="*25} Chain {i} {"="*25}')
        # kとvの幅を揃える
        for k, v in chain.items():
            if k == "transactions":
                print(k)
                for d in v:
                    print(f'{"-"*40}')
                    for kk, vv in d.items():
                        print(f"{kk:30}{vv}")
            else:
                print(f"{k:15}{v}")
    print(f'{"*"*25}')


def is_found_host(target, port):
    """
    他のノードが立ち上がっているか調べるsocket

    netword address: AF_INET
    TCP/IP: socket.SOCK_STREAM

    Parameters
    ----------  
    target : 

    port : 

    See Also
    --------
    # python blockchain_server.py
    # >>> is_found_host("127.0.0.1", 5000)
    # True
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.connect((target, port))
            return True
        except Exception as ex:
            logger.error({
                "action": "is_found_host",
                "target": target,
                "port": port,
                "ex": ex
            })
            return False


def find_neighbours(my_host, my_port, start_ip_range, end_ip_range, start_port, end_port):
    """
    nodeを検索する．    

    Parameters
    ----------
    my_host: int

    my_port: int

    start_ip_range : int

    end_ip_range : int

    start_port : int

    end_port : int

    Returns
    -------
    neighbours : list
        対象のサーバーを格納する

    See Also
    --------
    """
    address = f"{my_host}:{my_port}"
    m = RE_IP.search(my_host)
    if not m:
        return None

    prefix_host = m.group("prefix_host")
    last_ip = m.group("last_ip")

    neighbours = []
    for guess_port in range(start_port, end_port):
        for ip_range in range(start_ip_range, end_ip_range):
            guess_host = f"{prefix_host}{int(last_ip)+int(ip_range)}"
            guess_address = f"{guess_host}:{guess_port}"
            # ignored my_host
            if is_found_host(guess_host, guess_port) and not guess_address == address:
                neighbours.append(guess_address)
    return neighbours


def get_host():
    """
    socketで自身のホストのIPアドレスを探す    

    See Also
    --------
    """
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception as ex:
        logger.debug({"action": "get_host", "ex": ex})
    return "127.0.0.1"


if __name__ == "__main__":
    import doctest
    doctest.testmod()
