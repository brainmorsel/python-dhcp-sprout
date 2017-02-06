import ipaddress

from wtforms import Form
from wtforms import StringField
from wtforms import TextAreaField
from wtforms import validators
from wtforms import ValidationError


def str_to_ip_list(ip_list_str):
    if ip_list_str and isinstance(ip_list_str, str):
        return list(map(ipaddress.IPv4Address, ip_list_str.split()))
    return []


def validate_network_address(form, field):
    try:
        ipaddress.IPv4Network(field.data)
    except ValueError as e:
        raise ValidationError(str(e))


def validate_ip_address(form, field):
    try:
        ipaddress.IPv4Address(field.data)
    except ValueError as e:
        raise ValidationError(str(e))


def validate_ip_list(form, field):
    try:
        str_to_ip_list(field.data)
    except ValueError as e:
        raise ValidationError(str(e))


def filter_ip_list(ip_list):
    if not ip_list:
        return ''
    if isinstance(ip_list, str):
        return ip_list
    return '\n'.join(map(str, ip_list))


class ProfileEditForm(Form):
    name = StringField('Название', [validators.DataRequired()])
    description = TextAreaField('Описание')
    relay_ip = StringField('Relay IP', [validate_ip_address])
    router_ip = StringField('Router IP', [validate_ip_address])
    network_addr = StringField('Сеть', [validate_network_address])
    lease_time = StringField('Длительность аренды')
    dns_ips = TextAreaField('DNS IPs', [validate_ip_list], filters=[filter_ip_list])
    ntp_ips = TextAreaField('NTP IPs', [validate_ip_list], filters=[filter_ip_list])


class AssignedItemEditForm(Form):
    description = TextAreaField('Описание')
