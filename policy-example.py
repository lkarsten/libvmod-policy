#!/usr/bin/env python
"""
    Example Varnish policy vmod server.
"""
import socket
import struct
import SocketServer
import logging
from os.path import exists
from os import unlink
from pprint import pprint
from time import sleep

from VPOLServer import BaseVPOLRequestHandler

class SORBScheck(BaseVPOLRequestHandler):
    """
        Check if the requesting client is listed in the combined SORBS 
        blacklist.

        See http://www.sorbs.net/ for more information.

        Only checks IPv4, will allow any IPv6 client.
    """

    def policy(self):
        if "client_ip" not in self.meta:
            raise ClientError("No client_ip found")

        _ip = self.meta["client_ip"].split(".", 4)
        if len(_ip) != 4:
            self.request.send("200 DUNNO\n")
            return

        dnsname = "%s.%s.%s.%s.dnsbl.sorbs.net" % \
            (_ip[3], _ip[2], _ip[1], _ip[0])

        dnsres = None
        try:
            dnsres = socket.getaddrinfo(dnsname, None)
        except Exception as e:
            if e.errno == -2: # NXDOMAIN
                self.request.send("200 OK\n")
                return
            else:
                logging.debug(str(e))

        if dnsres:
            self.request.send("403 Forbidden\n")
        else:
            # unhandled response, fail gracefully.
            self.request.send("200 DUNNO\n")


class AllOKhandler(BaseVPOLRequestHandler):
    verbose = True
    def policy(self):
        if 1:
            pprint(self.meta)
            pprint(self.headers)
            pprint(self.body)

        response = "200 OK"
        self.request.send(response + "\n")
        print "Sent: %s" % response
        print "Request handling finished,"

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    socketfile = "/tmp/foo.sock";
    if exists(socketfile):
        unlink(socketfile)

    #server = SocketServer.UnixStreamServer(socketfile, AllOKhandler)
    server = SocketServer.UnixStreamServer(socketfile, SORBScheck)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
