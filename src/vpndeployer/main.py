#!/usr/bin/env python3
import argparse
import time
import requests
from vpndeployer import auth, droplets, ansible


def parse_args():
    parser = argparse.ArgumentParser(
        description="VPN Deploy Script with DigitalOcean")

    avaialble_distros = [
        'centos-7-x64',
        'fedora-27-x64',
        'fedora-28-x64',
        'ubuntu-18-10-x64',
        'ubuntu-14-04-x64',
    ]

    parser.add_argument("--ip", dest="ip", help="Your IP Address")
    parser.add_argument("--email", dest="email",
                        help="Email Address for OpenVPN download link")
    parser.add_argument("--name", default='VPN',
                        dest="name", help="Droplet Name")
    parser.add_argument("--region", default='nyc1',
                        dest="region", help="Droplet Region")
    parser.add_argument("--image", default='ubuntu-18-10-x64', dest="image", choices=avaialble_distros,
                        help="Droplet Distribution Image")

    return parser.parse_args()


def main():

    args = parse_args()

    DO_API_TOKEN = auth.ApiAuth.get_api_token()

    if args.ip is None:
        args.ip = requests.get("https://ipv4.icanhazip.com").text.strip('\n')

    if args.name == "VPN":
        args.name = args.name + "-" + str(time.time())

    ansible.gen_sshkey(DO_API_TOKEN)
    sshkey = droplets.get_sshkey_fingerprint(DO_API_TOKEN)

    print("\nDeploy Started!")
    print("This process typically takes less than 5 minutes.\n")

    droplets.create_droplet(ip=args.ip, name=args.name, region=args.region,
                            image=args.image, email=args.email, sshkey=sshkey, api_token=DO_API_TOKEN)
    time.sleep(10)
    droplet_ip = droplets.get_droplet_ip(
        name=args.name, api_token=DO_API_TOKEN)
    # TODO - Temporary fix to deploy occurring before droplet SSH connection is ready
    time.sleep(30)
    ansible.deploy_openvpn(ip=args.ip, email=args.email)

    # TODO - Add proper checking into the deploy, tenacity (below) should no longer be needed though.
    print(
        f"Deploy Completed!\n Download OpenVPN File: http://{droplet_ip}/client.ovpn")

    # @tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_fixed(20), retry=tenacity.retry_if_exception_type(IOError))
    # def check_deploy(droplet_ip):
    #     response = requests.get(f"http://{droplet_ip}/client.ovpn")
    #     if response.status_code == 200:
    #         raise IOError("Download File Unreachable!")
    #     else:
    #         print(f"Deploy Completed!\n Download OpenVPN File: http://{droplet_ip}/client.ovpn")

    # check_deploy(droplet_ip=droplet_ip)
