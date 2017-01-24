import sys
import asyncio
import logging.handlers
import signal
from configparser import ConfigParser

import click
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
import aiopg
import psycopg2.extras
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
import aiopg.sa

from . import db
from .dhcp.server import DHCPServer, DBChannelListener


def config_load(config_file):
    config = ConfigParser(allow_no_value=True)
    config.read(config_file)
    return config


class DiagnosticLogFilter:
    def filter(self, record):
        return 1 if record.levelno >= logging.WARNING else 0


def config_logging(config, log_level=None):
    log_level = log_level or config.get('log', 'level', fallback='info')
    log_format = config.get('log', 'format', fallback='%(asctime)s %(levelname)-8s %(name)s %(message)s')
    level = getattr(logging, log_level.upper())
    logging.basicConfig(level=level, format=log_format)

    http_access_file = config.get('log', 'http_access_file', fallback=None)
    if http_access_file:
        handler = logging.handlers.RotatingFileHandler(http_access_file, encoding='utf-8')
        access_logger = logging.getLogger('aiohttp.access')
        access_logger.addHandler(handler)

    diagnostic_file = config.get('log', 'diagnostic_file', fallback=None)
    if diagnostic_file:
        handler = logging.handlers.RotatingFileHandler(diagnostic_file, encoding='utf-8')
        handler.addFilter(DiagnosticLogFilter())
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)s %(message)s'))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)


async def config_db(config):
    db_engine = await aiopg.sa.create_engine(
        **config['database'])
    return db_engine


@click.command()
@click.option('-c', '--config', 'config_file', required=True, type=click.Path(exists=True, dir_okay=False))
@click.option('-l', '--log-level', 'log_level')
def dhcp_server(config_file, log_level):
    config = config_load(config_file)
    config_logging(config, log_level)
    logger = logging.getLogger(__name__)

    loop = asyncio.get_event_loop()
    try:
        loop.add_signal_handler(signal.SIGTERM, loop.stop)
    except NotImplementedError:
        # signals are not available on Windows
        pass

    logger.info('Init db connection...')
    db_engine = loop.run_until_complete(config_db(config))
    channel = DBChannelListener(config['database'], 'dhcp_control')
    loop.run_until_complete(channel.start())
    logger.info('Init dhcp server...')
    server = DHCPServer(db_engine, channel, config.get('dhcp', 'default_server_addr'))

    loop.run_until_complete(server.db_load_owners())

    binds = config.get('dhcp', 'binds').split()
    for bind in binds:
        if ':' in bind:
            host, port = bind.split(':')
        else:
            host, port = bind, 67
        server.bind(host, port=port)

    logger.info('Starting main loop...')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(server.stop())
        loop.run_until_complete(channel.stop())
        logger.info('Awaiting remaining tasks...')
        pending = asyncio.Task.all_tasks()
        loop.run_until_complete(asyncio.gather(*pending))
        loop.close()
        logger.info('Bye!')


@click.group()
@click.option('-c', '--config', 'config_file', type=click.Path(exists=True, dir_okay=False))
@click.option('-l', '--log-level', 'log_level')
@click.pass_context
def cli(ctx, config_file, log_level):
    if config_file:
        config = config_load(config_file)
        config_logging(config, log_level)
        ctx.obj = {'cfg': config}


@cli.group('db')
def cli_db():
    pass


@cli_db.command('init')
@click.pass_context
def cli_db_init(ctx):
    cfg = ctx.obj['cfg']
    db_conn_format = 'postgresql://{user}:{password}@{host}:{port}/{database}'
    db_uri = db_conn_format.format(**cfg['database'])
    engine = sa.create_engine(db_uri)
    with engine.connect() as conn:
        db.metadata.create_all(conn)


@cli.command('dhcp-bench')
@click.option('-T', '--threads', default=1)
@click.option('-1', '--oneshot', default=False, is_flag=True)
@click.option('-m', '--macaddr', default=None)
@click.option('-r', '--relay-ip', default=None)
@click.argument('address')  
def dhcp_bench(address, threads, oneshot, macaddr, relay_ip):
    from .dhcp import bench
    if oneshot:
        bench.oneshot(address, macaddr, relay_ip)
    else:
        bench.start_threaded(address, threads, macaddr, relay_ip)
