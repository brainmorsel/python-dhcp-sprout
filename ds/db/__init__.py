import sys
import ipaddress

import asyncio
from aiopg.sa import create_engine
from sqlalchemy.dialects import postgresql as pg
import sqlalchemy as sa
import psycopg2.extensions


metadata = sa.MetaData()


def cast_inet(value, cur):
    if value is None:
        return None
    return ipaddress.ip_address(value)


def cast_cidr(value, cur):
    if value is None:
        return None
    return ipaddress.ip_network(value)


# SELECT 'inet'::regtype::oid;
INET_OID = 869
INET = psycopg2.extensions.new_type((INET_OID,), "INET", cast_inet)
psycopg2.extensions.register_type(INET)

# SELECT 'cidr'::regtype::oid;
CIDR_OID = 650
CIDR = psycopg2.extensions.new_type((CIDR_OID,), "CIDR", cast_cidr)
psycopg2.extensions.register_type(CIDR)

# select typarray from pg_type where typname = 'inet'; -> 1041
psycopg2.extensions.register_type(
    psycopg2.extensions.new_array_type(
        (1041,), 'INET[]', INET))


def fit_params_dict(params, columns):
    ''' Делает копию словаря, содержащую только ключи соответсвующие полям таблицы.
    Такой словарь можно безопасно передать в .update() или .insert(), не опасаясь
    исключения "sqlalchemy.exc.CompileError: Unconsumed column names...".
    '''
    tbl_keys = {str(key) for key in columns}
    prm_keys = set(params.keys())
    keys = tbl_keys & prm_keys
    return {key: params[key] for key in keys}


profile = sa.Table(
    'profile', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('create_date', sa.DateTime(timezone=True), nullable=False,
              server_default=sa.func.now()),
    sa.Column('modify_date', sa.DateTime(timezone=True), nullable=False,
              server_default=sa.func.now()),
    sa.Column('name', sa.String, sa.CheckConstraint('length(name) > 0'), nullable=False),
    sa.Column('description', sa.String, nullable=False, server_default=''),
    sa.Column('relay_ip', pg.INET, nullable=False),
    sa.Column('router_ip', pg.INET, nullable=True),
    sa.Column('dns_ips', pg.ARRAY(pg.INET), nullable=True),
    sa.Column('ntp_ips', pg.ARRAY(pg.INET), nullable=True),
    sa.Column('lease_time', sa.Interval, nullable=False),
    sa.Column('network_addr', pg.CIDR, nullable=False),
    sa.UniqueConstraint('relay_ip'),
    sa.UniqueConstraint('name'),
)

owner = sa.Table(
    'owner', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('create_date', sa.DateTime(timezone=True), nullable=False,
              server_default=sa.func.now()),
    sa.Column('modify_date', sa.DateTime(timezone=True), nullable=False,
              server_default=sa.func.now()),
    sa.Column('lease_date', sa.DateTime(timezone=True), nullable=False,
              server_default=sa.func.now()),
    sa.Column('profile_id', sa.Integer, sa.ForeignKey('profile.id', ondelete='CASCADE'),
              nullable=False),
    sa.Column('ip_addr', pg.INET, nullable=True),
    sa.Column('mac_addr', pg.MACADDR, nullable=True, index=True),
    sa.Column('description', sa.String, nullable=False, server_default=''),
    sa.UniqueConstraint('profile_id', 'ip_addr'),
    sa.UniqueConstraint('profile_id', 'mac_addr'),
)
