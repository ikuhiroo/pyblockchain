import hashlib
import collections


def sorted_dict_by_key(unsorted_dict):
    """sorted by key
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
    # 出力形式
    for i, chain in enumerate(chains):
        print(f'{"="*25} Chain {i} {"="*25}')
        # kとvの幅を揃える
        for k, v in chain.items():
            if k == "transaction":
                print(k)
                for d in v:
                    print(f'{"-"*40}')
                    for kk, vv in d.items():
                        print(f'{kk:30}{vv}')
            else:
                print(f'{k:15}{v}')
    print(f'{"*"*25}')


if __name__ == "__main__":
    import doctest
    doctest.testmod()
