#!/usr/bin/env python

import sys
import time
import logging
import argparse
from shutil import which
from pathlib import Path

package_path = Path(__file__).resolve().parent
sys.path.append(str(package_path))

from lib import logger
from lib import util
from lib.ssh import SSHLoadBalancer
from lib.api import start_api
from lib.errors import *

log = logging.getLogger("trevorproxy.cli")

def main():
    parser = argparse.ArgumentParser(
        description="Round-robin requests through multiple reverse SSH SOCKs tunnels via a single master"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="be verbose"
    )
    parser.add_argument(
        "--api",
        default=31331,
        type=int,
        help="port that will be used by the API server (default: 31331)",
    )
    parser.add_argument(
        "--base",
        default=31332,
        type=int,
        help="base listening port to use for SOCKS proxies (default: 31332)",
    )

    try:
        options = parser.parse_args()

        if options.verbose:
            logging.getLogger("trevorproxy").setLevel(logging.DEBUG)

        # make sure executables exist
        for binary in SSHLoadBalancer.dependencies:
            if not which(binary):
                log.error(f"Please install {binary}")
                sys.exit(1)

        # init + add context for the API server
        load_balancer = SSHLoadBalancer(base_port=options.base)

        try:
            # start the load balancer and a HTTP API server which serves the next available port 
            # that can be used for a reverse SOCK connection
            load_balancer.start()
            start_api(port=options.api, context=load_balancer)

            # serve forever
            while 1:
                time.sleep(1)
                print("[INFO] Monitoring.  ", end="\r")

                # Check if new proxies have been added
                new = load_balancer.monitor_new_proxies()
                time.sleep(1)
                print("[INFO] Monitoring.. ", end="\r")

                # Check if all proxies are still up
                inactive = load_balancer.health_check_connections()
                time.sleep(1)
                print("[INFO] Monitoring...", end="\r")
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
