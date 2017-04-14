from collections import defaultdict

from . import dec
from . import enc
from .opttypes import OptionType
from .opttypes import AgentInformationOptionType


class Option:
    TYPE_ENUM = OptionType
    DECODERS = defaultdict(lambda: dec.default, {
        OptionType.Pad: dec.pad,
        OptionType.End: dec.pad,
        OptionType.ParameterRequestList: dec.parameters_request_list,
        OptionType.DHCPMessageType: dec.dchp_message_type,
    })
    ENCODERS = defaultdict(lambda: enc.default, {
        OptionType.Pad: enc.pad,
        OptionType.End: enc.pad,
        OptionType.DHCPMessageType: enc.uint8,
        OptionType.SubnetMask: enc.ip_address,
        OptionType.Router: enc.ip_address,
        OptionType.IPaddressLeaseTime: enc.uint32,
        OptionType.ServerIdentifier: enc.ip_address,
        OptionType.DomainNameServers: enc.ip_address_list,
        OptionType.HostName: enc.string,
        OptionType.NTPServer: enc.ip_address_list,
    })

    def __init__(self, type, value=None, _byte_size=0):
        self.type = type
        self.value = value
        self._byte_size = _byte_size

    def __repr__(self):
        return '{0} [size {2}]: {1}'.format(str(self.type), str(self.value), self._byte_size)

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_code = buffer[offset]
        try:
            type_code = cls.TYPE_ENUM(type_code)
        except ValueError:
            pass
        decoder = cls.DECODERS[type_code]
        value, size = decoder(buffer, offset)
        return cls(type_code, value, _byte_size=size)

    def pack_into(self, buffer, offset):
        encoder = self.ENCODERS[self.type]
        bytes_size = encoder(buffer, offset, self.type, self.value)
        return bytes_size


class AgentInformationSubOption(Option):
    TYPE_ENUM = AgentInformationOptionType
    DECODERS = defaultdict(lambda: dec.default)
    ENCODERS = defaultdict(lambda: enc.default)
