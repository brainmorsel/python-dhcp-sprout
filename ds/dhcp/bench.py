import logging
import socket
import threading
import time


from .proto.packet import Packet
from .proto.opttypes import OptionType
from .proto.dhcpmsg import MessageType


def sync_worker(address, on_success, on_fail, oneshot=False, macaddr=None, relay_ip=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 0))
    sock.settimeout(1)

    pkt = Packet(message_type=MessageType.REQUEST)
    pkt.op = Packet.Op.REQUEST
    pkt.chaddr = macaddr or 'de:12:44:4c:bb:48'
    if relay_ip:
        pkt.hops = 1
        pkt.giaddr = relay_ip

    while True:
        data = pkt.pack()
        sent = sock.sendto(data, address)
        try:
            data, address = sock.recvfrom(4096)
            on_success()
            if oneshot:
                reply = Packet.unpack_from(data)
                print(reply)
        except socket.timeout:
            on_fail()
        if oneshot:
            break


def start_threaded(address, threads=1, macaddr=None, relay_ip=None):
    host, port = address.split(':')
    port = int(port)

    success_count = 0
    fail_count = 0

    def inc_success():
        nonlocal success_count
        success_count += 1

    def inc_fail():
        nonlocal fail_count
        fail_count += 1

    for _ in range(threads):
        t = threading.Thread(target=sync_worker, args=((host, port), inc_success, inc_fail, False, macaddr, relay_ip), daemon=True)
        t.start()

    while True:
        time.sleep(1.0)
        print('requests success: %s fail: %s' % (success_count, fail_count))
        success_count = 0
        fail_count = 0


def oneshot(address, macaddr, relay_ip):
    host, port = address.split(':')
    port = int(port)
    sync_worker((host, port), lambda:None, lambda:None, oneshot=True, macaddr=macaddr, relay_ip=relay_ip)
