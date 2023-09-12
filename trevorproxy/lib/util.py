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

from http.server import BaseHTTPRequestHandler, HTTPServer
#import SocketServer - TODO remove if unnecessary

log = logging.getLogger("trevorproxy.util")

class BasicAPIHandler(BaseHTTPRequestHandler):
    def __init__(self, load_balancer, *args):
        self.context = load_balancer
        super().__init__(self, *args)

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-Type', 'plain/text')
        self.end_headers()
        
    # GET sends back next available port
    def do_GET(self):
        next_port = self.context.next_available_proxy_port(self.address_string())
        self._set_headers()
        self.wfile.write(next_port)


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
