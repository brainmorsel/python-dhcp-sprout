from setuptools import setup, find_packages

setup(
    name='ds',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'uvloop',
        'aiopg',
        'psycopg2',
        'sqlalchemy',
        'aiohttp',
        'aiohttp-jinja2',
        'aiohttp-session',
        'cryptography',
        'wtforms',
    ],
    entry_points='''
        [console_scripts]
        ds-dhcp-server=ds.cli:dhcp_server
        ds-web-server=ds.cli:web_server
        ds-cli=ds.cli:cli
    ''',
    )
