from enum import IntEnum


class OptionType(IntEnum):
    # RFC1497 vendor extensions
    Pad = 0
    End = 255
    SubnetMask = 1
    TimeOffset = 2
    Router = 3
    TimeServer = 4
    NameServer = 5
    DomainNameServers = 6
    LogServer = 7
    CookieServer = 8
    LPRServer = 9
    ImpressServer = 10
    ResourceLocationServer = 11
    HostName = 12
    BootFileSize = 13
    MeritDumpFile = 14
    DomainName = 15
    SwapServer = 16
    RootPath = 17
    ExtensionsPath = 18
    # IP Layer Parameters per Host
    IPForwarding = 19
    NonLocalSourceRouting = 20
    PolicyFilter = 21
    MaxDatagramReassemblySize = 22
    DefaultIPTTL = 23
    PathMTUAgingTimeout = 24
    PathMTUPlateauTable = 25
    # IP Layer Parameters per Interface
    InterfaceMTU = 26
    AllSubnetsAreLocal = 27
    BroadcastAddress = 28
    PerformMaskDiscovery = 29
    MaskSupplier = 30
    PerformRouterDiscovery = 31
    RouterSolicitationAddress = 32
    StaticRoute = 33
    # Link Layer Parameters per Interface
    TrailerEncapsulationOption = 34
    ARPCacheTimeout = 35
    EthernetEncapsulation = 36
    # TCP Parameters
    TCPDefaultTTL = 37
    TCPKeepaliveInterval = 38
    TCPKeepaliveGarbage = 39
    # Application and Service Parameters
    NISDomain = 40
    NIServers = 41
    NTPServer = 42
    VendorSpecificInformation = 43
    NetBIOSNameServer = 44
    NetBIOSDDS = 45
    NetBIOSNodeType = 46
    NetBIOSScope = 47
    XWindowFontServer = 48
    XWindowDisplayManager = 49
    NISPlusDomain = 64
    NISPlusServers = 65
    MobileIPHomeAgent = 68
    SMTPServer = 69
    POP3Server = 70
    NNTPServer = 71
    DefaultWWWServer = 72
    DefaultFingerServer = 73
    DefaultIRCServer = 74
    StreetTalkServer = 75
    StreetTalkDirectoryAssistanceServer = 76
    # DHCP Extensions
    RequestedIPaddress = 50
    IPaddressLeaseTime = 51
    OptionOverload = 52
    DHCPMessageType = 53
    ServerIdentifier = 54
    ParameterRequestList = 55
    DHCPMessage = 56
    MaximumDHCPMessageSize = 57
    RenewalTime = 58
    RebindingTime = 59
    VendorClassIdentifier = 60
    ClientIdentifier = 61
    TFTPServerName = 66
    BootfileName = 67
    # Other:
    ClientFQDN = 81  # RFC 4702
    AgentInformation = 82


class AgentInformationOptionType(IntEnum):
    CircuitID = 1
    RemoteID = 2
