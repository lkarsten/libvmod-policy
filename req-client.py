#!/usr/bin/env python
#
# This would be what Varnish does.
#
import struct
import socket
from time import sleep, time
from pprint import pprint

from VPOLServer import parse_header

# no empty ending lines.
req = ["""
vcl_method: 1
client_identity: 127.0.0.1
t_open: %s
http_method: 1
URL: /
proto: HTTP/1.1
""" % time(),
"""Host: localhost
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: nb-NO,nb;q=0.8,no;q=0.6,nn;q=0.4,en-US;q=0.2,en;q=0.2
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.3
User-Agent: curl 1.2
Cache-Control: no-cache
Cookie: __utma=253898641.2098534993.1348749499.1374491627.1374580772.70; __utmz=2538986 41.1348749499.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)
""",
"this is the post body"]

class ServerError(Exception):
    pass


def main_unix():
    import logging
    logging.basicConfig(level=logging.DEBUG)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect("/tmp/foo.sock")

#    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, 2)
#    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, 2)
#    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    xid = 12345
    headercontent = (1, 0, xid, len(req[0]), len(req[1]), len(req[2]))
    # print headercontent
    header = "VPOL" + struct.pack("!HHQIIQ", *headercontent)
    print len(header)
    sock.send(header + "".join(req))
    print "done sending, reading response"

    response = ''
    waited = 0.0

    if 0:
#    while True:
        try:
            r = sock.recv(32, socket.MSG_DONTWAIT)
        except Exception as e:
            if e.errno == 11: # not yet
                waited += 0.01
                sleep(0.01)
            else:
                print dir(e)
                print str(e)
        else:
            if len(r) == 0:
                waited += 0.01
                sleep(0.01)
            else:
                print "got %i bytes" % len(r)
                response += r
                if len(r) >= 3:
                    break
        if waited >= 2:
            raise ServerError("timeout after %ss" % waited)

    r = sock.recv(32)
    header = parse_header(r, is_request=False)
    meta = sock.recv(header["len_meta"])
    addheaders = sock.recv(header["len_headers"])
    newbody = sock.recv(header["len_body"])

    pprint(meta)
    pprint(addheaders)
    pprint(newbody)

    #print "response: %s" % response.strip()

if __name__ == "__main__":
    main_unix()
