import datetime

from aiohttp import web
from aiohttp_jinja2 import template
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
import psycopg2

from ds import db
from . import forms


@template('index.jinja2')
async def index(request):
    return {}


@template('profile_list.jinja2')
async def profile_list(request):
    async with request.app.db.acquire() as conn:
        items = await (await conn.execute(
            sa.select([db.profile]).
            select_from(
                db.profile
            ).
            order_by(db.profile.c.name)
        )).fetchall()
    return {'items': items}


def _cast_str_to_inet_arr(ip_list_str):
    return sa.cast(map(str, forms.str_to_ip_list(ip_list_str)), pg.ARRAY(pg.INET))


@template('profile_edit.jinja2')
async def profile_edit(request):
    tbl = db.profile
    item_id = request.match_info.get('id')
    await request.post()
    async with request.app.db.acquire() as conn:
        async with conn.begin():
            item = await (await conn.execute(
                tbl.select().where(tbl.c.id == item_id)
            )).fetchone()
            form = forms.ProfileEditForm(request.POST, item)
            if request.method == 'POST' and form.validate():
                params = db.fit_params_dict(form.data, tbl.c.keys())
                print(params['dns_ips'])
                params['dns_ips'] = _cast_str_to_inet_arr(params['dns_ips'])
                params['ntp_ips'] = _cast_str_to_inet_arr(params['ntp_ips'])
                if item_id is None:
                    await conn.execute(tbl.insert().values(params))
                else:
                    await conn.execute(
                        tbl.update().values(params).where(tbl.c.id == item_id)
                    )
                    await conn.execute(
                        sa.select([sa.func.pg_notify('dhcp_control', 'RELOAD_PROFILE {}'.format(item_id))])
                    )

                return web.HTTPFound('/profile/')

        return {'form': form}


async def profile_delete(request):
    tbl = db.profile
    item_id = request.match_info.get('id')
    async with request.app.db.acquire() as conn:
        await conn.execute(tbl.delete().where(tbl.c.id == item_id))
        return web.HTTPFound('/profile/')


@template('staging_list.jinja2')
async def staging_list(request):
    async with request.app.db.acquire() as conn:
        items = await (await conn.execute(
            sa.select([
                db.owner,
                db.profile.c.name.label('profile_name'),
                db.profile.c.relay_ip,
            ]).
            select_from(
                db.owner.
                join(db.profile)
            ).
            where(db.owner.c.ip_addr == None).
            order_by(sa.desc(db.owner.c.create_date))
        )).fetchall()
        return {'items': items}


async def staging_assign_ip(request):
    item_id = int(request.match_info.get('id'))
    async with request.app.db.acquire() as conn:
        async with conn.begin():
            profile_id = await conn.scalar(
                sa.select([db.owner.c.profile_id]).where(db.owner.c.id == item_id)
            )
            gen = sa.select([
                (sa.cast('0.0.0.0', pg.INET) + sa.func.generate_series(
                    sa.cast(db.profile.c.network_addr, pg.INET) - '0.0.0.0' + 1,
                    sa.func.broadcast(db.profile.c.network_addr) - '0.0.0.0' - 1
                )).label('ip_addr')
            ]).\
                select_from(db.profile.join(db.owner)). \
                where(db.profile.c.id == profile_id)
            sel = sa.select([db.owner.c.ip_addr]). \
                where(db.owner.c.profile_id == profile_id). \
                where(db.owner.c.ip_addr != None)
            ip_addr = gen.except_(sel).order_by('ip_addr').limit(1)
            await conn.execute(
                db.owner.update().values(
                    ip_addr=ip_addr,
                    modify_date=sa.func.now()
                ).
                where(db.owner.c.id == item_id)
            )
            await conn.execute(
                sa.select([sa.func.pg_notify('dhcp_control', 'RELOAD_ITEM {}'.format(item_id))])
            )
        return web.HTTPFound('/staging/')


async def staging_delete(request):
    tbl = db.owner
    item_id = request.match_info.get('id')
    async with request.app.db.acquire() as conn:
        async with conn.begin():
            mac_addr = await conn.scalar(
                sa.select([tbl.c.mac_addr]).
                where(tbl.c.id == item_id)
            )
            await conn.execute(tbl.delete().where(tbl.c.id == item_id))
            await conn.execute(
                sa.select([sa.func.pg_notify('dhcp_control', 'REMOVE_STAGING {}'.format(mac_addr))])
            )
        return web.HTTPFound('/staging/')


@template('assigned_list.jinja2')
async def assigned_list(request):
    async with request.app.db.acquire() as conn:
        items = await (await conn.execute(
            sa.select([
                db.owner,
                db.profile.c.name.label('profile_name'),
                db.profile.c.relay_ip,
            ]).
            select_from(
                db.owner.
                join(db.profile)
            ).
            where(db.owner.c.ip_addr != None).
            order_by(sa.desc(db.owner.c.lease_date))
        )).fetchall()
        return {'items': items}


async def assigned_delete(request):
    tbl = db.owner
    item_id = request.match_info.get('id')
    async with request.app.db.acquire() as conn:
        async with conn.begin():
            mac_addr = await conn.scalar(
                sa.select([tbl.c.mac_addr]).
                where(tbl.c.id == item_id)
            )
            await conn.execute(tbl.delete().where(tbl.c.id == item_id))
            await conn.execute(
                sa.select([sa.func.pg_notify('dhcp_control', 'REMOVE_ACTIVE {}'.format(mac_addr))])
            )
        return web.HTTPFound('/assigned/')
