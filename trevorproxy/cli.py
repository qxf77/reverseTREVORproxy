#!/usr/bin/env python

# by TheTechromancer

import sys
import time
import logging
import argparse
from shutil import which
from pathlib import Path

package_path = Path(__file__).resolve().parent
sys.path.append(str(package_path))

import lib.logger
from lib import util
from lib import logger
from lib.errors import *

log = logging.getLogger("trevorproxy.cli")


def main():
    parser = argparse.ArgumentParser(
        description="Round-robin requests through multiple REVERSE SSH tunnels via a single SOCKS server"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Be quiet")
    parser.add_argument(
        "-v", "-d", "--verbose", "--debug", action="store_true", help="Be verbose"
    )

    subparsers = parser.add_subparsers(dest="proxytype", help="proxy type")

    ssh = subparsers.add_parser("ssh", help="round-robin traffic through SSH hosts")
    
    #ssh.add_argument(
    #    "-k", "--key", help="Use this SSH key when connecting to proxy hosts"
    #)
    #ssh.add_argument("-kp", "--key-pass", action="store_true", help=argparse.SUPPRESS)
    ssh.add_argument(
        "--base-port",
        default=32482,
        type=int,
        help="Base listening port to use for SOCKS proxies (default: 32482)",
    )
    #ssh.add_argument(
    #    "--active-connections-file",
    #    "-f",
    #    required=True,
    #    help="File containing a list of current active connections. This file will be monitored for \
    #        additions and removals and traffic will be load-balanced accordinly (user@host)",
    #)

    try:
        options = parser.parse_args()

        if not options.quiet:
            logging.getLogger("trevorproxy").setLevel(logging.DEBUG)

        if options.proxytype == "ssh":
            from lib.ssh import SSHLoadBalancer

            # make sure executables exist
            for binary in SSHLoadBalancer.dependencies:
                if not which(binary):
                    log.error(f"Please install {binary}")
                    sys.exit(1)

            # init 
            load_balancer = SSHLoadBalancer(base_port=options.base_port)

            # Check if active connection are still alive
            #load_balancer.health_check_connections()
            

            #f_hosts = open(options.hosts_file, "r")
            #hosts = f_hosts.read().splitlines()
            #load_balancer.load_proxies_from_file(hosts)

            try:
                # start the load balancer and a HTTP API server which serves the next available port 
                # that can be used for a reverse SOCK connection
                load_balancer.start()
                load_balancer.start_api()

                # serve forever
                while 1:
                    # Check if new proxies have been added
                    new = load_balancer.monitor_new_proxies()

                    # Check if all proxies are still up
                    inactive = load_balancer.health_check_connections()

                    # If there are changes to the proxy list then restart the load balancer to use the new connections
                    '''if new or inactive:
                        if new and inactive:
                            msg = "new proxies have been added and inactive proxies have been removed"
                        elif new:
                            msg = "new proxies have been added"
                        else:
                            msg = "inactive proxies have been removed"
                        
                        log.info(f"Restarting load balancer - {msg}")
                        load_balancer.restart()'''

                    #load_balancer.start()
                    #log.info(
                    #    f"Listening on socks5://{options.listen_address}:{options.port}"
                    #)
                    """                 
                    try:
                        f_hosts = open(options.hosts_file, "r")
                        m_hosts = f_hosts.read().splitlines()
                        a_hosts = [h for h in m_hosts if h not in hosts]  # every host that is defined in the file (m_hosts) but does not exist in the current list (hosts) should be added
                        d_hosts = [h for h in hosts if h not in m_hosts]  # every host that is was previously defined (hosts) but is not present anymore in the file (m_hosts) should be removed

                        # add newly added hosts to the load balancer
                        if a_hosts:
                            [load_balancer.add_proxy(add_host) for add_host in a_hosts]
                            a_hosts = []
                            hosts = m_hosts

                        if d_hosts:
                            [load_balancer.remove_proxy(remove_host) for remove_host in d_hosts]
                            d_hosts = []
                            hosts = m_hosts
                    except:
                        log.error("Cannot read SSH hosts file") 
                    
                        
                    # rebuild proxy if it goes down
                    for proxy in load_balancer.proxies.values():
                        if not proxy.is_connected():
                            log.debug(
                                f"SSH Proxy {proxy} went down, attempting to rebuild"
                            )
                            proxy.start()
                    time.sleep(1)
                    """

            finally:
                load_balancer.stop()


    except argparse.ArgumentError as e:
        log.error(e)
        log.error("Check your syntax")
        sys.exit(2)

    except TrevorProxyError as e:
        log.error(f"Error in TREVORproxy: {e}")

    except Exception as e:
        if options.verbose:
            import traceback

            log.error(traceback.format_exc())
        else:
            log.error(f"Unhandled error (-v to debug): {e}")

    except KeyboardInterrupt:
        log.error("Interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
