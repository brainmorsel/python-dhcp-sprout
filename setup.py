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
    ],
    entry_points='''
        [console_scripts]
        ds-dhcp-server=ds.cli:dhcp_server
        ds-cli=ds.cli:cli
    ''',
    )
