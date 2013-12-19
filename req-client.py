#!/usr/bin/env python
#
# This would be what Varnish does.
#
import struct
import socket
from time import sleep, time

# no empty ending lines.
req = ["""xid: 12345
vcl_method: 1
client_ip: 127.0.0.1
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

if __name__ == "__main__":
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect("/tmp/foo.sock")

#    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, 2)
#    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, 2)
#    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    headercontent = (len(req[0]), len(req[1]), len(req[2]))
    # print headercontent

    header = "VPOL01" + struct.pack("!III", *headercontent)
    # print len(header)
    sock.send(header)
    sock.send(req[0])
    sock.send(req[1])
    sock.send(req[2])

    response = ''
    waited = 0.0
    while True:
        try:
            r = sock.recv(1500, socket.MSG_DONTWAIT)
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
                #print "got %i bytes" % len(r)
                #print r
                response += r
                if len(r) >= 3:
                    break
        if waited >= 2:
            raise ServerError("timeout after %ss" % waited)

    print "response: %s" % response.strip()
