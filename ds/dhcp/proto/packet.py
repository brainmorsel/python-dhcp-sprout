import ipaddress
import struct
from enum import IntEnum

from ..util import mac_to_string
from ..util import mac_to_bytes
from .option import Option
from .option import AgentInformationSubOption
from .opttypes import OptionType
from .opttypes import AgentInformationOptionType
from .dhcpmsg import MessageType


MAC_ADDRESS_LEN = 6
MIN_PACKET_LEN = 576


class HardwareAddressType(IntEnum):
    # we only support Ethernet hardware address type
    ETHERNET = 1


class Packet:
    class Op(IntEnum):
        REQUEST = 1
        REPLY = 2

    STRUCT = struct.Struct('!4BL2H4L16s64s128s')
    FIELD_NAMES = 'op htype hlen hops xid secs flags ciaddr yiaddr siaddr giaddr chaddr sname file'.split()
    _IP_FIELDS = ['ciaddr', 'yiaddr', 'siaddr', 'giaddr']
    F_BROADCAST = 0x8000
    MAGIC_COOKIE = bytes([99, 130, 83, 99])

    def __init__(self, *, message_type=None, options=None, _field_values=None):
        self._options = options or []
        self.message_type = message_type

        if _field_values:
            if len(_field_values) != len(self.FIELD_NAMES):
                raise ValueError('Values count not match fields count.')
            for field, value in zip(self.FIELD_NAMES, _field_values):
                if field in self._IP_FIELDS:
                    value = ipaddress.IPv4Address(value)
                self.__dict__[field] = value
            self.op = self.Op(self.op)
            self.htype = HardwareAddressType(self.htype)
            if self.hlen != MAC_ADDRESS_LEN:
                raise ValueError('Invalid hardware address size.')
            self.chaddr = mac_to_string(self.chaddr[:MAC_ADDRESS_LEN])
            self.sname, _, _ = self.sname.partition(b'\0')
            self.file, _, _ = self.file.partition(b'\0')
        else:
            self.op = self.Op.REQUEST
            self.htype = HardwareAddressType.ETHERNET
            self.hlen = MAC_ADDRESS_LEN
            self.hops = 0
            self.xid = 0
            self.secs = 0
            self.flags = 0
            self.chaddr = '00:00:00:00:00:00'
            self.sname = b''
            self.file = b''
            for field in self._IP_FIELDS:
                self.__dict__[field] = ipaddress.IPv4Address(0)

    def __repr__(self):
        parts = ['DHCPPacket:']
        for field in self.FIELD_NAMES:
            parts.append('  {0}: {1}'.format(field, str(self.__dict__[field])))
        if self.message_type:
            parts.append('  MessageType: {0}'.format(str(self.message_type)))
        if self._options:
            parts.append('  Options:')
            for o in self._options:
                parts.append('    {0}'.format(o))
        return '\n'.join(parts)

    def add_option(self, type_code, value):
        self._options.append(Option(type_code, value))

    def reset_options(self):
        self._options = []

    def get_circuit_id(self):
        opt_value = b''
        for o in self._options:
            if o.type == OptionType.AgentInformation:
                opt_value = o.value
                break

        offset = 0
        while offset < len(opt_value):
            sub_opt = AgentInformationSubOption.unpack_from(opt_value, offset)
            if sub_opt.type == AgentInformationOptionType.CircuitID:
                return sub_opt.value
        return None

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        values = cls.STRUCT.unpack_from(buffer, offset=offset)
        options = []
        message_type = None
        offset += cls.STRUCT.size
        if len(buffer) > offset:
            if buffer[offset:offset + 4] != cls.MAGIC_COOKIE:
                raise ValueError('Options magic cookie not matched.')
            offset += 4
            while offset < len(buffer):
                option = Option.unpack_from(buffer, offset)
                offset += option._byte_size
                if option.type == OptionType.End:
                    break
                if option.type == OptionType.Pad:
                    continue
                if option.type == OptionType.DHCPMessageType:
                    message_type = MessageType(option.value)
                    continue
                options.append(option)
        return cls(options=options, _field_values=values, message_type=message_type)

    def pack_into(self, buffer, offset=0):
        values = (
            self.op,
            self.htype,
            self.hlen,
            self.hops,
            self.xid,
            self.secs,
            self.flags,
            int(ipaddress.IPv4Address(self.ciaddr)),
            int(ipaddress.IPv4Address(self.yiaddr)),
            int(ipaddress.IPv4Address(self.siaddr)),
            int(ipaddress.IPv4Address(self.giaddr)),
            mac_to_bytes(self.chaddr),
            self.sname,
            self.file
        )
        self.STRUCT.pack_into(buffer, offset, *values)
        offset += self.STRUCT.size

        if self._options or self.message_type:
            buffer[offset:offset + 4] = self.MAGIC_COOKIE
            offset += 4

            if self.message_type is not None:
                msg_opt = Option(OptionType.DHCPMessageType, self.message_type)
                offset += msg_opt.pack_into(buffer, offset)

            for option in self._options:
                offset += option.pack_into(buffer, offset)
            offset += Option(OptionType.End).pack_into(buffer, offset)

        return offset

    def pack(self):
        buffer = bytearray(MIN_PACKET_LEN)
        size = self.pack_into(buffer)
        return buffer[:size]

    def make_reply(self, server_addr, offered_addr):
        if self.message_type == MessageType.DISCOVER:
            pkt = self.__class__(message_type=MessageType.OFFER)
        elif self.message_type == MessageType.REQUEST:
            pkt = self.__class__(message_type=MessageType.ACK)
        else:
            raise ValueError('Can reply only to DISCOVER or REQUEST.')
        pkt.op = self.Op.REPLY
        pkt.xid = self.xid
        pkt.chaddr = self.chaddr
        pkt.siaddr = ipaddress.IPv4Address(server_addr or '0.0.0.0')
        pkt.yiaddr = ipaddress.IPv4Address(offered_addr)
        pkt.giaddr = ipaddress.IPv4Address(self.giaddr)
        pkt.hops = self.hops
        return pkt
