import socket
import os
import logging
import subprocess as sp

log = logging.getLogger("trevorproxy.util")

def is_port_in_use(port: int) -> bool:
    # https://stackoverflow.com/questions/2470971/fast-way-to-test-if-a-port-is-in-use-using-python#answers
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def sudo_run(cmd, *args, **kwargs):
    if os.geteuid() != 0:
        cmd = ["sudo"] + cmd
    log.debug(" ".join(cmd))
    return sp.run(cmd, *args, **kwargs)
