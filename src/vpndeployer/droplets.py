#!/usr/bin/env python3
import requests
import re
import digitalocean
from vpndeployer import ansible
import tenacity
import paramiko
import warnings


class DropletNotFound(Exception):
    """Droplet cannot be found."""


class IPNotFound(Exception):
    """Droplet Public IP cannot be found."""


def create_droplet(api_token, ip, name, region, image, email, sshkey):
    droplet = digitalocean.Droplet(
        token=f'{api_token}',
        name=f'{name}',
        region=f'{region}',
        image=f'{image}',
        ssh_keys=sshkey,
        size_slug='512mb',
        user_data=f"""#!/bin/bash
    if [[ -e /etc/debian_version ]]; then
        apt-get -y install python-minimal
    else
        yum -y install python-minimal
    fi
    """,
    )

    return droplet.create()


@tenacity.retry(stop=tenacity.stop_after_attempt(10), wait=tenacity.wait_fixed(2), reraise=True)
def get_droplet_ip(name, api_token):
    droplet_list = requests.get(f"https://api.digitalocean.com/v2/droplets", headers={
                                "Authorization": "Bearer %s" % api_token, "Content-Type": "application/json"})
    for item in droplet_list.json()['droplets']:
        if item['name'] == name:
            droplet_vpn = item
            break
    else:
        raise DropletNotFound('Droplet Not Found')

    for item in droplet_vpn['networks']['v4']:
        # TODO - Grab first IP from json array without a break
        droplet_ip = item['ip_address']
        break
    else:
        raise IPNotFound('Droplet IP Not Found')

    return droplet_ip


@tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_fixed(20), reraise=True)
def check_droplet_connection(ip):
    # Temporary fix due to deprecation warnings. Awaiting https://github.com/paramiko/paramiko/pull/1379
    warnings.filterwarnings(action='ignore', module='.*paramiko.*')
    data_path = ansible.playbook_path()
    private_key = data_path + '/env/ssh_key'
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=ip, username='root', key_filename=private_key)
    ssh_client.close()


def add_sshkey(api_token):
    data_path = ansible.playbook_path()
    public_key = open(data_path + '/env/ssh_key.pub').read()
    addkey = digitalocean.SSHKey(
        token=api_token, name='VPN-Deployer', public_key=public_key)

    return addkey.create()


def get_sshkey_fingerprint(api_token):
    manager = digitalocean.Manager(token=api_token)
    sshkeys = manager.get_all_sshkeys()
    fingerprint = [str(re.findall('[0-9]* VPN-Deployer', str(sshkeys)))[2:10]]

    return [int(key) for key in fingerprint]
