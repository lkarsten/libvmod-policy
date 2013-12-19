#!/usr/bin/env python

import socket
import struct
import SocketServer
from os.path import exists
from os import unlink
from pprint import pprint
from time import sleep
import logging

class ClientError(Exception):
    pass

class BaseVPOLRequestHandler(SocketServer.StreamRequestHandler):
    timeout = 0.5
    #timeout = 2
    def handle(self):
        logging.debug("connection accepted")
        if 0:
            print "sleeping .. "
            sleep(10000)

        section = 0
        data = [[], [], []]
        rfile = self.request.makefile()
        logging.debug("reading header")

        header = rfile.read(6+3*4)
        if len(header) < 10:
            raise ClientError("chunked/partial header not ok")

        logging.debug("got header: (%i) \"%s\"" % (len(header), header))
        if not header[0:6] == "VPOL01":
            raise ClientError("pre-header")

        for i in range(6, len(header), 4):
            logging.debug("index %i: %s" % (i, " ".join(
                    [ "%s" % hex(ord(x)) for x in header[i:i+4]])))

        try:
            lengths = struct.unpack("!III", header[6:6+3*4])
        except ValueError as e:
            raise ClientError("header" + str(e))

        for i, l in enumerate(lengths):
            if l > 1e5:
                raise ClientError("Field %i too large" % i)
        try:
            logging.debug("reading %i bytes of meta" % lengths[0])
            self.meta = rfile.read(lengths[0])
            # print "meta is: \"%s\"" % meta

            logging.debug("reading %i bytes of headers" % lengths[1])
            self.headers = rfile.read(lengths[1])
            # print "headers are: \"%s\"" % headers

            logging.debug("reading %i bytes of body" % lengths[2])
            self.body = rfile.read(lengths[2])
            #print "body is: %i" % len(body)
        except socket.error as e:
            raise ClientError("read: " + str(e))

        _ = {}
        for line in self.meta.split("\n"):
            if len(line) == 0:
                continue
            k, v = line.split(": ", 1)
            _[k] = v
        self.meta = _

        _ = {}
        for line in self.headers.split("\n"):
            if len(line) == 0:
                continue
            k, v = line.split(": ", 1)
            _[k] = v
        self.headers = _

        self.policy()


    def policy(self):
        """
            Override this with your application logic.
        """
        raise NotImplementedError()


class AllOKhandler(BaseVPOLRequestHandler):
    def policy(self):
        if 1:
            pprint(self.meta)
            pprint(self.headers)
            pprint(self.body)
        # let the policy daemon vouch for the client for a while. ttl, ip.
        #self.request.send("policy-whitelist-client: 3600,1.2.3.4\n")
        response = "200 OK"
        self.request.send(response + "\n")
        print "Sent: %s" % response
        print "Request handling finished,"

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    socketfile = "/tmp/foo.sock";
    if exists(socketfile):
        unlink(socketfile)
    server = SocketServer.UnixStreamServer(socketfile, AllOKhandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

