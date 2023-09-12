import requests
import socket
import os
import json
import logging
import ipaddress
import subprocess as sp
from pathlib import Path
from getpass import getpass
from contextlib import suppress

log = logging.getLogger("trevorproxy.util")

def monitor(api_key):
    url = "https://api.tailscale.com/api/v2/tailnet/-/devices?fields=all"
    headers = { "Authorization" : "Bearer f{api_key}" }
    r = requests.get(url, headers=headers)
    
    devices = json.loads(r.text)["devices"]

    # Get all IPv4 addresses in TailScale
    hosts = []
    for d in devices:
        hosts.append(d.get("addresses")[0])

def is_port_in_use(port: int) -> bool:
    # https://stackoverflow.com/questions/2470971/fast-way-to-test-if-a-port-is-in-use-using-python#answers
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def sudo_run(cmd, *args, **kwargs):
    if os.geteuid() != 0:
        cmd = ["sudo"] + cmd
    log.debug(" ".join(cmd))
    return sp.run(cmd, *args, **kwargs)
