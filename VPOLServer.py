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
    def handle(self):
        logging.debug("connection accepted")
        if 0:
            print "sleeping .. "
            sleep(10000)

        header_length = 32

        self.rfile = self.request.makefile()
        logging.debug("reading header")

        header = self.rfile.read(header_length)
        if len(header) < 14:
            raise ClientError("chunked/partial header not ok")

        logging.debug("got header: (%i) \"%s\"" % (len(header), header))
        if not header[0:4] == "VPOL":
            raise ClientError("pre-header")

        try:
            protoversion, rcode, self.vxid, l_meta, l_headers, l_body = \
               struct.unpack("!HHQIIQ", header[4:header_length])
        except ValueError as e:
            raise ClientError("header" + str(e))

        if protoversion != 1:
            raise ClientError("protocol version")

        #for i in range(6, len(header), 4):
        #    logging.debug("index %i: %s" % (i, " ".join(
        #            [ "%s" % hex(ord(x)) for x in header[i:i+4]])))
        if rcode != 0:
            raise ClientError("Request rcode %s is not zero", rcode)
        if self.vxid == 0:
            raise ClientError("Invalid zero req vxid %s", self.vxid)

        for i in [l_meta, l_headers, l_body]:
            if i > 1e5:
                raise ClientError("Field too large")
        try:
            #logging.debug("reading %i bytes of meta" % lengths[0])
            self.meta = self.rfile.read(l_meta)
            # print "meta is: \"%s\"" % meta

            #logging.debug("reading %i bytes of headers" % lengths[1])
            self.headers = self.rfile.read(l_headers)
            # print "headers are: \"%s\"" % headers

            #logging.debug("reading %i bytes of body" % lengths[2])
            self.body = self.rfile.read(l_body)
            #print "body is: %i" % len(body)
        except socket.error as e:
            raise ClientError("read: %s", str(e))

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


    def respond(self, rcode, respmeta, respheaders, respbody):
        if type(respmeta) == dict:
            respmeta = "\n".join([ "%s: %s" % (x[0], x[1]) for x in respmeta.items()])

        if type(respheaders) == dict:
            respheader = "\n".join([ "%s: %s" % (x[0], x[1]) for x in respheader.items()])

        header = struct.pack("!HHQIIQ", 1, \
            rcode, self.vxid, len(respmeta), len(respheaders), len(respbody))
        self.request.send(header)

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
        self.respond(200, {}, {"foo: bar"}, "response body")
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

