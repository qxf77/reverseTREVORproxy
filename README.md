# reverseTREVORproxy

[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](https://raw.githubusercontent.com/blacklanternsecurity/nmappalyzer/master/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.6+-blue)](https://www.python.org)

## Installation
~~~bash
pip install git+https://github.com/qxf77/reverseTREVORproxy
~~~

## How it works
reverseTREVORproxy listens for incoming SSH connections that start a reverse SOCKS proxy and allows you to round-robin packets through them.

## CLI Usage
~~~
$ trevorproxy -h
usage: trevorproxy [-h] [-v] [--api API] [--base BASE]

Round-robin requests through multiple reverse SSH SOCKs tunnels via a single master

options:
  -h, --help     show this help message and exit
  -v, --verbose  be verbose
  --api API      port that will be used by the API server (default: 31331)
  --base BASE    base listening port to use for SOCKS proxies (default: 31332)
~~~

## Original by [@thetechr0mancer](https://twitter.com/thetechr0mancer)
See the accompanying [**Blog Post**](https://github.com/blacklanternsecurity/TREVORspray/blob/trevorspray-v2/blogpost.md) for a fun rant and some cool demos!
  
A SOCKS proxy written in Python that randomizes your source IP address. Round-robin your evil packets through SSH tunnels or give them billions of unique source addresses!
