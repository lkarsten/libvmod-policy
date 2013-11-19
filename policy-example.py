#!/usr/bin/env python

import socket
import SocketServer
from pprint import pprint

class policyTCPHandler(SocketServer.StreamRequestHandler):
    timeout = 0.5
    def handle(self):
        section = 0
        data = [[], [], []]
        rfile = self.request.makefile()
        while section < len(data):
            try:
                line = rfile.readline()
                if len(line) == 0:
                    raise EOFError()
                print "read line: (%i) \"%s\"" % (len(line), line.strip())
            except socket.error as e:
                print "socketerror " + str(e)
                return
            if line in ["\r\n", "\n"]:
                section += 1
            else:
                data[section].append(line)

        pprint(data)
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

