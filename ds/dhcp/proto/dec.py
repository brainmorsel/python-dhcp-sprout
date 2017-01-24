from .dhcpmsg import MessageType
from .opttypes import OptionType


def default(buffer, offset):
    value_len = buffer[offset + 1]
    value = buffer[offset + 2:offset + 2 + value_len]
    size = 2 + value_len
    return value, size


def pad(buffer, offset):
    return None, 1


def parameters_request_list(buffer, offset):
    value_len = buffer[offset + 1]
    value = []
    for type_code in buffer[offset + 2:offset + 2 + value_len]:
        try:
            value.append(OptionType(type_code))
        except ValueError:
            value.append(type_code)
    size = 2 + value_len
    return value, size


def dchp_message_type(buffer, offset):
    value = MessageType(buffer[offset + 2])
    size = 3
    return value, size
