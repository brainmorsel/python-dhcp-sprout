# Install

    mkvirtualenv ds
    pip install -e .
    sudo -u postgres psql -c "CREATE USER dhcp_sprout WITH PASSWORD 'dhcp_sprout_pass';"
    sudo -u postgres psql -c "CREATE DATABASE dhcp_sprout_db WITH OWNER = dhcp_sprout;"
