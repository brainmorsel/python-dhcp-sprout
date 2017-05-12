import struct
import ipaddress


ST_UINT32 = struct.Struct('!I')


def default(buffer, offset, type_code, value:bytes):
    bytes_size = 2 + len(value)
    buffer[offset] = type_code
    buffer[offset + 1] = len(value)
    buffer[offset + 2:offset + bytes_size] = value
    return bytes_size


def pad(buffer, offset, type_code, value):
    bytes_size = 1
    buffer[offset] = type_code
    return bytes_size


def uint8(buffer, offset, type_code, value):
    bytes_size = 3
    buffer[offset] = type_code
    buffer[offset + 1] = 1
    buffer[offset + 2] = int(value)
    return bytes_size


def uint32(buffer, offset, type_code, value):
    bytes_size = 6
    buffer[offset] = type_code
    buffer[offset + 1] = 4
    ST_UINT32.pack_into(buffer, offset + 2, int(value))
    return bytes_size


def ip_address(buffer, offset, type_code, value):
    bytes_size = 6
    buffer[offset] = type_code
    buffer[offset + 1] = 4
    ST_UINT32.pack_into(buffer, offset + 2, int(ipaddress.IPv4Address(value)))
    return bytes_size


def ip_address_list(buffer, offset, type_code, value):
    bytes_size = 2 + 4 * len(value)
    buffer[offset] = type_code
    buffer[offset + 1] = 4 * len(value)
    for idx, ip in enumerate(value):
        off = offset + 2 + 4 * idx
        ST_UINT32.pack_into(buffer, off, int(ipaddress.IPv4Address(ip)))
    return bytes_size


def string(buffer, offset, type_code, value:str):
    if isinstance(value, str):
        value = value.encode('utf-8')
    return default(buffer, offset, type_code, value)
