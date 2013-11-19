#!/usr/bin/env python
#
# This would be what Varnish does.
#
import struct
import socket

# no empty ending lines.
req = ["""src: 127.0.0.1
srcport: 1234
""",
"""Host: localhost
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: nb-NO,nb;q=0.8,no;q=0.6,nn;q=0.4,en-US;q=0.2,en;q=0.2
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.3
User-Agent: curl 1.2
Cache-Control: no-cache
Cookie: __utma=253898641.2098534993.1348749499.1374491627.1374580772.70; __utmz=2538986 41.1348749499.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)
""",
"this is the post body"]

DELIM="\n"

if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 15696))

    headercontent = (len(req[0]), len(req[1]), len(req[2]))
    header = "VPOL" + struct.pack(">HHL", *headercontent)
    sock.send(header)
    sock.send(req[0])
    sock.send(req[1])
    sock.send(req[2])

    response = sock.recv(1500)
    if len(response) == 0:
        print "Connection closed"
    else:
        print "response: %s" % response

