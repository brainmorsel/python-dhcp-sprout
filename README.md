# Install

    virtualenv -p python3 venv
    PATH=$PATH:/usr/pgsql-9.6/bin/ ./venv/bin/pip install -e .
    sudo -u postgres psql -c "CREATE USER dhcp_sprout WITH PASSWORD 'dhcp_sprout_pass';"
    sudo -u postgres psql -c "CREATE DATABASE dhcp_sprout_db WITH OWNER = dhcp_sprout;"
    ./venv/bin/ds-cli -c config.ini db init
