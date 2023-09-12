import sh
import logging
from time import sleep
import subprocess as sp
from pathlib import Path

from http.server import HTTPServer
from .util import BasicAPIHandler

from .util import sudo_run, is_port_in_use
#from .errors import SSHProxyError

log = logging.getLogger("trevorproxy.ssh")


class SSHProxy:
    def __init__(self, host, proxy_port):
        self.host = host
        self.proxy_port = proxy_port

    def get_remote_host(self):
        return self.host

    def get_local_proxy_port(self):
        return self.host

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return f"socks5://127.0.0.1:{self.proxy_port}"

    def __repr__(self):
        return str(self)


class IPTables:
    def __init__(self, proxies, address=None, proxy_port=None):
        if address is None:
            self.address = "127.0.0.1"
        else:
            self.address = str(address)
        if proxy_port is None:
            self.proxy_port = 1080
        else:
            self.proxy_port = int(proxy_port)

        self.proxies = [p for p in proxies if p is not None]

        self.iptables_rules = []

    def start(self):
        log.debug("Creating iptables rules")

        current_ip = False
        for i, proxy in enumerate(self.proxies):
            if proxy is not None:
                iptables_add = ["iptables", "-A"]
                iptables_main = [
                    "OUTPUT",
                    "-t",
                    "nat",
                    "-d",
                    f"{self.address}",
                    "-o",
                    "lo",
                    "-p",
                    "tcp",
                    "--dport",
                    f"{self.proxy_port}",
                    "-j",
                    "DNAT",
                    "--to-destination",
                    f"127.0.0.1:{proxy.proxy_port}",
                ]

                # if this isn't the last proxy
                if not i == len(self.proxies) - 1:
                    iptables_main += [
                        "-m",
                        "statistic",
                        "--mode",
                        "nth",
                        "--every",
                        f"{len(self.proxies)-i}",  # can't change this to start from low to high since that's how iptables evaluates the rules
                        "--packet",
                        "0",
                    ]

                self.iptables_rules.append(iptables_main)

                cmd = iptables_add + iptables_main
                sudo_run(cmd)

    def stop(self):
        log.debug("Cleaning up iptables rules")

        for rule in self.iptables_rules:
            iptables_del = ["iptables", "-D"]
            cmd = iptables_del + rule
            sudo_run(cmd)

    def add_rule(self, proxy):
        # not very optimized
        self.stop()
        self.proxies.append(proxy)
        self.iptables_rules = []
        self.start()

    def remove_rule(self, proxy):
        # not very optimized
        self.stop()
        self.proxies.remove(proxy)
        self.iptables_rules = []
        self.start()

    def update_proxies(self, proxies):
        self.proxies = proxies


class SSHLoadBalancer:
    dependencies = ["ssh", "ss", "iptables", "sudo"]

    def __init__(
        self,
        hosts=None,
        base_port=33482,
        current_ip=False,               # not used
        socks_server=True,
        context=None
    ):
        self.hosts = hosts
        self.active_proxies = dict()    # all current active proxies 
        self.all_proxies = dict()       # all proxies, even ones that don't have an active connection yet
        
        self.base_port = base_port
        self.socks_server = socks_server

        self.iptables = IPTables(list(self.active_proxies.values()))
        self.proxy_round_robin = list(self.active_proxies.values())
        self.round_robin_counter = 0

    def add_context(self, context):
        self.context = context

    def handler(*args):
        # https://python-list.python.narkive.com/9Q8NM4nH/passing-context-into-basehttprequesthandler
        BasicAPIHandler(self.context, *args)

    def start_api(self, address="0.0.0.0", port=8080):
        '''
        Start a HTTP server acting as a basic API 
        '''
        server_address = (address, port)
        httpd = HTTPServer(server_address, handler)
            
        log.debug(f"[*] Starting API on {address}:{port}")
        httpd.serve_forever()

    def monitor_new_proxies(self):
        '''
        Monitor for incoming proxies - if a new entry is added to all_proxies then this entry is verified if it can be moved to active_proxies
        '''
        new = False
        if self.all_proxies == self.active_proxies:
            return new

        new_proxies = set(self.all_proxies) - set(self.active_proxies)
        for proxy in new_proxies:
            if check_if_proxy_is_established(self.all_proxies[proxy]):
                new = True
                add_connection_active(self.all_proxies[proxy])
                log.info(f"New reverse SOCKS on 127.0.0.1:{proxy.get_local_proxy_port} from {proxy.get_remote_host()}")
        
        return new
    
    def health_check_connections(self):
        '''
        Check if the active connections are still established
        '''
        inactive = False

        for proxy in list(self.active_proxies):  # use list(proxies) in instead of proxies.values() to avoid runtime deletion error
            if not check_if_proxy_is_established(self.active_proxies[proxy]):
                inactive = True
                remove_connection(self.active_proxies[proxy])
                log.info(f"Removed reverse SOCKS on 127.0.0.1:{proxy.get_local_proxy_port} from {proxy.get_remote_host()}")
        
        return inactive

    def check_if_proxy_is_established(self, proxy):
        '''
        See if the PROXY actually has an established ssh reverse SOCKS
        '''
        port = proxy.get_local_proxy_port()

        cmd = ["ss", "-Hlt4", "state", "all", "sport", "=", f":{port}"]
        ret = sudo_run(cmd, capture_output=True)

        if ret.stdout:
            return True
        else:
            return False

    # TODO implement lease time - if a connection is not created within x seconds after releasing a port then the port should be available in the pool
    def next_available_proxy_port(self, remote_host):
        '''
        RETURN next available port that can be used for a reverse SOCKS connection
        ADD the SSH proxy to the temporary list
        '''
        for port in range(self.base_port, self.base_port + 5000):  # NOTE: up to 5000 simultaneous reverse socks connections can be made and used?
            if not is_port_in_use(port):
                break

        new_conn_inactive(SSHProxy(remote_host, port))
        return port

    def new_conn_inactive(self, proxy):
        '''
        Save a potential new active connection
        '''
        self.all_proxies[str(proxy)] = proxy
    
    def new_conn_active(self, proxy):
        '''
        Add a new active connection, update iptables
        '''
        self.active_proxies[str(proxy)] = proxy
        self.iptables.add_rule(proxy)
        self.proxy_round_robin = list(self.active_proxies.values())


    def remove_connection(self, proxy):
        '''
        Remove a single active connection, update iptables
        '''
        cmd = ["ss", "-KHt4", "state", "established", "sport", "=", ":ssh", "and", "dst", "=", proxy.get_remote_host()]
        sudo_run(cmd)

        del self.active_proxies[str(proxy)]
        self.iptables.remove_rule(proxy)
        self.proxy_round_robin = list(self.active_proxies.values())


    def remove_all_connections(self):
        '''
        Remove all active connections, don't update iptables after every delete
        '''
        for proxy in self.active_proxies.values():
            del self.active_proxies[str(proxy)]
            cmd = ["ss", "-KHt4", "state", "established", "sport", "=", ":ssh", "and", "dst", "=", proxy.get_remote_host()]
            sudo_run(cmd)

    def start(self):
        '''
        Start the load balancer
        '''
        if self.socks_server:
            self.iptables.start()

    def restart(self):
        '''
        Restart the load balancer to update rules
        '''
        if self.socks_server:
            self.iptables.stop()
            self.iptables.update_proxies(list(self.active_proxies.values()))
            self.iptables.start()

            self.proxy_round_robin = list(self.active_proxies.values())
            self.round_robin_counter = 0

    def stop(self):
        '''
        Kill all connections
        '''
        self.remove_all_connections()
        
        if self.socks_server:
            self.iptables.stop()

    def __next__(self):
        """
        Yields proxies in round-robin fashion forever
        Note that a proxy can be "None" if current_ip is specified
        """

        proxy_num = self.round_robin_counter % len(self.active_proxies)
        proxy = self.proxy_round_robin[proxy_num]
        self.round_robin_counter += 1
        return proxy

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        debug.info("Shutting down proxies")
        self.stop()
