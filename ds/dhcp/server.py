import asyncio
from enum import Enum
import logging
import socket
from collections import defaultdict
import ipaddress
import time
from datetime import datetime

import aiopg
from sqlalchemy.dialects import postgresql as pg
import sqlalchemy as sa
import psycopg2

from .proto.packet import Packet
from .proto.opttypes import OptionType
from .proto.dhcpmsg import MessageType
from ds import db


class BindToDeviceError(Exception): pass


class _Listener:
    def __init__(self, interface, reader, loop, *, port=67, server_addr=None, bufsize=4096, wqueue=10):
        self.interface = interface
        self.server_addr = None
        self.bufsize = bufsize
        self.loop = loop
        self._reader = reader
        self._is_writing = False
        self._write_queue = asyncio.Queue(wqueue, loop=loop)
        self.logger = logging.getLogger(__name__)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(False)
        sock.bind((interface, int(port)))

        self.loop.add_reader(sock.fileno(), self._handle_read)
        self._s = sock

        if interface != '0.0.0.0':
            self.server_addr = interface

        self.logger.info('listener binded to %s:%s', interface, port)

    def _handle_read(self):
        data, address = self._s.recvfrom(self.bufsize)
        self.logger.debug('listener %s: recieved %d octets from %s', self.interface, len(data), address)
        future = self._reader(self, address, data)
        asyncio.ensure_future(future, loop=self.loop)

    def _handle_write(self):
        try:
            address, data = self._write_queue.get_nowait()
            sent = self._s.sendto(data, address)
            self.logger.debug('listener %s: sent %d/%d octets to %s', self.interface, sent, len(data), address)
        except asyncio.QueueEmpty:
            self.loop.remove_writer(self._s.fileno())
            self._is_writing = False

    async def _write(self, address, data):
        if not self._is_writing:
            self.loop.add_writer(self._s.fileno(), self._handle_write)
            self._is_writing = True
        await self._write_queue.put((address, data))

    async def send(self, address, data):
        host, port = address
        if host == '0.0.0.0':
            address = ('255.255.255.255', port)
        await self._write(address, data)


class AsyncServer:
    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self._listeners = {}
        self.logger = logging.getLogger(__name__)

    def bind(self, interface, **kwargs):
        self._listeners[interface] = _Listener(interface, self._handle_packet, self.loop, **kwargs)

    async def _handle_packet(self, listener, address, data):
        try:
            pkt = Packet.unpack_from(data)

            if pkt.op == Packet.Op.REQUEST:
                reply_pkt = await self.handle_request(pkt, address, listener)
            elif pkt.op == Packet.Op.REPLY:
                reply_pkt = await self.handle_reply(pkt, address, listener)
            else:
                reply_pkt = None

            if reply_pkt:
                reply_pkt.op = Packet.Op.REPLY
                reply_pkt.flags = 0
                data = reply_pkt.pack()
                pkt = Packet.unpack_from(data)
                await listener.send(address, data)
        except Exception:
            self.logger.exception('an error occured when handling input packet from %s (%s)', listener.interface, address)

    async def handle_request(self, pkt, address, listener):
        return None

    async def handle_reply(self, pkt, address, listener):
        return None


class DBTask(Enum):
    SHUTDOWN = 0  # Завершить обрабутку
    LOAD_OWNERS = 1  # Загрузить весь список привязок
    ADD_STAGING = 2  # Добавить в список ожидающих привязки
    UPDATE_LEASE = 3  # Обновить дату последней аренды
    RELOAD_ITEM = 4  # перезагрузить профиль для указаной записи
    REMOVE_STAGING = 5  # удалить MAC из staging кэша
    REMOVE_ACTIVE = 6  # удалить MAC из активного кэша
    RELOAD_PROFILE = 7  # перезагрузить все записи с заданым профилем


class DBChannelListener:
    def __init__(self, conn_params, channel):
        self.conn_params = conn_params
        self.channel = channel
        self.queue = None

    async def start(self):
        self.conn = await aiopg.connect(**self.conn_params)
        async with self.conn.cursor() as cur:
            await cur.execute('LISTEN {}'.format(self.channel))
        self.queue = self.conn.notifies

    async def stop(self):
        self.conn.close()
        await self.queue.put(None)


class DHCPServer(AsyncServer):
    sql_select_owner = sa.select([
        db.profile.c.relay_ip,
        db.profile.c.router_ip,
        db.profile.c.network_addr,
        db.profile.c.lease_time,
        db.profile.c.dns_ips,
        db.profile.c.ntp_ips,
        db.owner.c.mac_addr,
        db.owner.c.ip_addr,
        db.owner.c.id,
    ]).select_from(
        db.owner.join(db.profile)
    )
    def __init__(self, db, channel, default_server_addr=None, loop=None):
        super().__init__(loop)
        self.default_server_addr = default_server_addr

        self.db = db
        self.channel = channel
        self.db_tasks = asyncio.Queue(maxsize=1000, loop=loop)
        self.maps = {}
        self.maps_staging = {}

        future = self.db_task_handling_loop()
        asyncio.ensure_future(future, loop=self.loop)
        future = self.db_channel_handling_loop()
        asyncio.ensure_future(future, loop=self.loop)
        self.is_stoping = False

    async def stop(self):
        self.logger.info('Started grace shutdown...')
        self.is_stoping = True
        await self.db_tasks.put((DBTask.SHUTDOWN, None))

    async def handle_request(self, request, address, listener):
        if self.is_stoping:
            return None

        if request.message_type is None:
            return None

        if request.message_type not in (MessageType.DISCOVER, MessageType.REQUEST):
            return None

        if not request.hops:
            # обрабатывать только запросы с релеев
            return None

        relay_ip = request.giaddr or ipaddress.IPv4Address(address)
        self.logger.info('%s %s from relay: %s', request.chaddr, request.message_type.name, relay_ip)
        
        if request.chaddr in self.maps:
            profile = self.maps[request.chaddr]
            if profile['relay_ip'] != relay_ip and request.chaddr not in self.maps_staging:
                self.db_task_add_staging(request.chaddr, relay_ip)
                return None
        elif request.chaddr in self.maps_staging:
            self.logger.debug('%s is awaiting resolution, ignore request', request.chaddr)
            return None
        else:
            self.db_task_add_staging(request.chaddr, relay_ip)
            return None

        server_addr = listener.server_addr or self.default_server_addr
        pkt = request.make_reply(server_addr, profile['ip_addr'])
        if pkt.message_type == MessageType.ACK:
            self.db_task_update_lease(request.chaddr, relay_ip)

        pkt.add_option(OptionType.SubnetMask, profile['netmask'])
        if profile.get('router_ip'):
            pkt.add_option(OptionType.Router, profile['router_ip'])
        if profile.get('dns_ips'):
            pkt.add_option(OptionType.DomainNameServers, profile['dns_ips'])
        if profile.get('ntp_ips'):
            pkt.add_option(OptionType.NTPServer, profile['ntp_ips'])
        lease_time = int(profile['lease_time'].total_seconds())
        pkt.add_option(OptionType.IPaddressLeaseTime, lease_time)
        if server_addr:
            pkt.add_option(OptionType.ServerIdentifier, server_addr)
        return pkt

    def db_task_add_staging(self, macaddr, relay_ip):
        try:
            task = DBTask.ADD_STAGING, (datetime.now(), macaddr, relay_ip)
            self.db_tasks.put_nowait(task)
            self.maps_staging[macaddr] = relay_ip
        except asyncio.QueueFull:
            self.logger.warning('db tasks queue is full, new task droped')

    def db_task_update_lease(self, macaddr, relay_ip):
        try:
            task = DBTask.UPDATE_LEASE, (datetime.now(), macaddr, relay_ip)
            self.db_tasks.put_nowait(task)
        except asyncio.QueueFull:
            self.logger.warning('db tasks queue is full, new task droped')

    async def db_task_handling_loop(self):
        async with self.db.acquire() as conn:
            while True:
                task, params = await self.db_tasks.get()
                self.logger.info('handling db task: %s', task.name)
                if task is DBTask.SHUTDOWN:
                    break
                elif task is DBTask.ADD_STAGING:
                    date, mac_addr, relay_ip = params
                    try:
                        res = await (await conn.execute(
                            db.owner.insert().from_select(
                                ['mac_addr', 'profile_id'],
                                sa.select([sa.literal(mac_addr), db.profile.c.id]).
                                    select_from(db.profile).
                                    where(db.profile.c.relay_ip == str(relay_ip))
                            ).returning(db.owner.c.id)
                        )).fetchone()
                        if not res:
                            del  self.maps_staging[mac_addr]
                            self.logger.warning('no profile for relay %s', relay_ip)
                    except psycopg2.IntegrityError:
                        pass
                elif task is DBTask.UPDATE_LEASE:
                    date, macaddr, relay_ip = params
                    item = self.maps.get(macaddr)
                    if item:
                        await conn.execute(
                            db.owner.update().
                                values(lease_date=date).
                                where(db.owner.c.id == item['id'])
                        )
                elif task is DBTask.REMOVE_ACTIVE:
                    mac_addr, = params
                    del self.maps[mac_addr]
                elif task is DBTask.REMOVE_STAGING:
                    mac_addr, = params
                    del self.maps_staging[mac_addr]
                elif task is DBTask.RELOAD_ITEM:
                    item_id, = params
                    item = await (await conn.execute(
                        self.sql_select_owner.where(db.owner.c.id == item_id)
                    )).fetchone()
                    self._update_item(item)
                elif task is DBTask.RELOAD_PROFILE:
                    profile_id, = params
                    items = await conn.execute(
                        self.sql_select_owner.
                            where(db.owner.c.profile_id == profile_id).
                            order_by(sa.asc(db.owner.c.modify_date))
                    )
                    async for item in items:
                        self._update_item(item)

        self.db.close()
        await self.db.wait_closed()

    async def db_load_owners(self):
        async with self.db.acquire() as conn:
            items = await (await conn.execute(
                self.sql_select_owner.order_by(sa.asc(db.owner.c.modify_date))
            )).fetchall()
            for item in items:
                self._update_item(item)

    def _update_item(self, item):
        if item.ip_addr:
            if item.mac_addr in self.maps_staging:
                del self.maps_staging[item.mac_addr]
            self.maps[item.mac_addr] = dict(item)
            self.maps[item.mac_addr]['netmask'] = item.network_addr.with_netmask.split('/')[1]
        else:
            self.maps_staging[item.mac_addr] = item.relay_ip

    async def db_channel_handling_loop(self):
        while True:
            msg = await self.channel.queue.get()
            if msg is None:
                break
            self.logger.info('got channel msg: %s', msg.payload)
            action, param = msg.payload.split(' ', 1)
            if action == 'RELOAD_ITEM':
                item_id = int(param)
                task = DBTask[action], (item_id,)
                await self.db_tasks.put(task)
            elif action in ('REMOVE_STAGING', 'REMOVE_ACTIVE'):
                mac_addr = param.lower()
                task = DBTask[action], (mac_addr,)
                await self.db_tasks.put(task)
            elif action == 'RELOAD_PROFILE':
                profile_id = int(param)
                task = DBTask[action], (profile_id,)
                await self.db_tasks.put(task)
