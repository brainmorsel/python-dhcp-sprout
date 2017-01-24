from enum import IntEnum

 
class MessageType(IntEnum):
    DISCOVER = 1
    OFFER = 2
    REQUEST = 3
    DECLINE = 4
    ACK = 5
    NAK = 6
    RELEASE = 7
    # rfc2132
    INFORM = 8
    # rfc4388
    LEASEQUERY = 10
    LEASEUNASSIGNED = 11
    LEASEUNKNOWN = 12
    LEASEACTIVE = 13
