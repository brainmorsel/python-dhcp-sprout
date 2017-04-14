# Install

    mkdir /opt/ds && cd ds
    git clone https://github.com/brainmorsel/python-dhcp-sprout.git
    useradd -d /opt/ds -r ds
    virtualenv -p python3 venv
    PATH=$PATH:/usr/pgsql-9.6/bin/ ./venv/bin/pip install -e python-dhcp-sprout
    sudo -u postgres psql -c "CREATE USER dhcp_sprout WITH PASSWORD 'dhcp_sprout_pass';"
    sudo -u postgres psql -c "CREATE DATABASE dhcp_sprout_db WITH OWNER = dhcp_sprout;"
    cp python-dhcp-sprout/example/config.ini /opt/ds/config.ini
    cp python-dhcp-sprout/example/*.service /etc/systemd/system/
    ./venv/bin/ds-cli -c config.ini db init
    systemctl start ds-web-server
    systemctl start ds-dhcp-server

# Extra Links

https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol
http://www.iana.org/assignments/bootp-dhcp-parameters/bootp-dhcp-parameters.xml
https://tools.ietf.org/html/rfc2132
