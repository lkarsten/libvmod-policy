#!/usr/bin/env python

import socket
import struct
import SocketServer
from pprint import pprint

class ClientError(Exception):
    pass

class policyTCPHandler(SocketServer.StreamRequestHandler):
    timeout = 0.5
    def handle(self):
        section = 0
        data = [[], [], []]
        rfile = self.request.makefile()

        header = rfile.read(12)
        if not header[0:4] == "VPOL":
            raise ClientError("pre-header")

        try:
            lengths = struct.unpack(">HHL", header[4:12])
        except ValueError as e:
            raise ClientError("header" + str(e))

        for l in lengths:
            if l > 1e6:
                return

        try:
            meta = rfile.read(lengths[0])
            headers = rfile.read(lengths[1])
            body = rfile.read(lengths[2])
        except socket.error as e:
            raise ClientError("read: " + str(e))


        pprint(meta)
        pprint(headers)
        pprint(body)
        # let the policy daemon vouch for the client for a while. ttl, ip.
        #self.request.send("policy-whitelist-client: 3600,1.2.3.4\n")
        self.request.send("OK\n")
        print "Request handling finished"


if __name__ == "__main__":
    HOST, PORT = "localhost", 15696
    SocketServer.TCPServer.allow_reuse_address = True
    server = SocketServer.TCPServer((HOST, PORT), policyTCPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

