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

from lib.api import start_api

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
    
    ssh.add_argument(
        "--base-port",
        default=32482,
        type=int,
        help="Base listening port to use for SOCKS proxies (default: 32482)",
    )

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

            # init + add context for the API server
            load_balancer = SSHLoadBalancer(base_port=options.base_port)

            try:
                # start the load balancer and a HTTP API server which serves the next available port 
                # that can be used for a reverse SOCK connection
                load_balancer.start()
                start_api(context=load_balancer)

                # serve forever
                while 1:
                    # Check if new proxies have been added
                    new = load_balancer.monitor_new_proxies()

                    # Check if all proxies are still up
                    inactive = load_balancer.health_check_connections()

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
