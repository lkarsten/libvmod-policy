#!/usr/bin/env python

import socket
import struct
import SocketServer
from pprint import pprint

class ClientError(Exception):
    pass

class policyTCPHandler(SocketServer.StreamRequestHandler):
    #timeout = 0.5
    timeout = 2
    def handle(self):
        print "connection accepted"
        section = 0
        data = [[], [], []]
        rfile = self.request.makefile()
        print "reading header"
        header = rfile.read(12)
        print "got header: %i bytes" % len(header)
        if not header[0:4] == "VPOL":
            raise ClientError("pre-header")

        try:
            lengths = struct.unpack(">HHL", header[4:12])
        except ValueError as e:
            raise ClientError("header" + str(e))
        print lengths

        for l in lengths:
            if l > 1e6:
                return

        try:
            print "reading %i bytes of meta" % lengths[0]
            meta = rfile.read(lengths[0])
            print "reading %i bytes of headers" % lengths[1]
            headers = rfile.read(lengths[1])
            print "reading %i bytes of body" % lengths[2]
            body = rfile.read(lengths[2])
        except socket.error as e:
            raise ClientError("read: " + str(e))

        pprint(meta)
        pprint(headers)
        pprint(body)
        # let the policy daemon vouch for the client for a while. ttl, ip.
        #self.request.send("policy-whitelist-client: 3600,1.2.3.4\n")
        response = "200 OK"
        self.request.send(response + "\n")
        print "Sent: %s" % response
        print "Request handling finished,"


if __name__ == "__main__":
    HOST, PORT = "localhost", 15696
    SocketServer.TCPServer.allow_reuse_address = True
    server = SocketServer.TCPServer((HOST, PORT), policyTCPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

