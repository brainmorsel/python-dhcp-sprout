import binascii
from collections import defaultdict


def mac_to_string(addr_bytes):
    return ':'.join('%02x' % b for b in addr_bytes)


_cleanup_table = defaultdict(lambda: None, {ord(c): c for c in '0123456789abcdefABCDEF'})
def mac_to_bytes(addr_string):
    return binascii.unhexlify(addr_string.translate(_cleanup_table))
