import _thread as thread
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
#import SocketServer - TODO remove if unnecessary

log = logging.getLogger("trevorproxy.api")

class BasicAPIHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-Type', 'plain/text')
        self.end_headers()
        
    # GET sends back next available port
    def do_GET(self):
        next_port = self.server.context.next_available_proxy_port(self.address_string())
        self._set_headers()
        self.wfile.write(str(next_port).encode())
    
    # Don't log new connections in the tty
    # https://stackoverflow.com/questions/3389305/how-to-silent-quiet-httpserver-and-basichttprequesthandlers-stderr-output
    def log_message(self, format, *args):
        return

class BasicAPIServer(HTTPServer):
    '''
    Custom API server with a refernce to the SSH load balancer
    # https://python-list.python.narkive.com/9Q8NM4nH/passing-context-into-basehttprequesthandler
    '''
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.context = None

    def add_context(self, context):
        self.context = context

def start_api(address="0.0.0.0", port=8080, context=None):
    '''
    Start a HTTP server acting as a basic API 
    '''
    server_address = (address, port)
    httpd = BasicAPIServer(server_address, BasicAPIHandler)
    httpd.add_context(context)
        
    log.debug(f"[*] Starting API on {address}:{port}")
    thread.start_new_thread(httpd.serve_forever,())
