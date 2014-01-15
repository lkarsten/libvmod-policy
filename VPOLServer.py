#!/usr/bin/env python

import socket
import struct
import SocketServer
from os.path import exists
from os import unlink
from pprint import pprint
from time import sleep
import logging

class FormatError(Exception):
    pass

class ClientError(Exception):
    pass



def parse_header(header, is_request=True):
    """
    >>> parse_header(b"VPOL1\x20")
    {'protoversion': 1, 'rcode': 0, 'vxid': 0, 'len_meta': 0, 'len_headers': 0,
    'len_body': 0}
    """
    HEADER_LENGTH = 32

    logging.debug("got header: (%i) \"%s\"" % (len(header), header))
    logging.debug("header: %s", " ".join(x.encode('hex') for x in header))

    if not header[0:4] == "VPOL":
        raise FormatError("pre-header")

    try:
        _x = struct.unpack("!HHQIIQ", header[4:HEADER_LENGTH])
        assert len(_x) == 6
    except ValueError as e:
        raise FormatError("header error: " + str(e))

    pprint(_x)
    if _x[0] != 1:
        raise FormatError("Protocol version")

    res = {'protoversion': _x[0], 'rcode': _x[1], 'vxid': _x[2],
           'len_meta': _x[3], 'len_headers': _x[4], 'len_body': _x[5]}

    #for i in range(6, len(header), 4):
    #    logging.debug("index %i: %s" % (i, " ".join(
    #            [ "%s" % hex(ord(x)) for x in header[i:i+4]])))
    if is_request:
        if res["rcode"] != 0:
            raise FormatError("Request rcode %s is not zero", res["rcode"])
        if res["vxid"] == 0:
            raise FormatError("Invalid zero req vxid %s", res["vxid"])
    else:
        if res["vxid"] == 0:
            raise FormatError("Invalid zero resp vxid %s", res["vxid"])


    #print "header is: "
    #pprint(res)
    return res


def write_header(response):
    raise NotImplementedError()

    assert type(response) == dict

    xid = 12345
    headercontent = (1, 0, xid, len(req[0]), len(req[1]), len(req[2]))
    # print headercontent

    header = "VPOL1" + struct.pack("!HHQIIQ", *headercontent)
    # print len(header)
    return header


class BaseVPOLRequestHandler(SocketServer.StreamRequestHandler):
    #timeout = 0.5
    timeout = 2
    def handle(self):
        logging.debug("connection accepted")
        if 0:
            print "sleeping .. "
            sleep(10000)

        header_length = 32
        self.rfile = self.request.makefile()
        logging.debug("reading header")

        headerdata = self.rfile.read(header_length)
        print "got %i bytes" % len(headerdata)

        if len(headerdata) < 14:
            raise FormatError("chunked/partial header not ok")

        header = parse_header(headerdata)


        for i in ['len_meta', 'len_headers', 'len_body']:
            if header[i] > 1e5:
                raise FormatError("Field %s is to big" % i)
        try:
            #logging.debug("reading %i bytes of meta" % lengths[0])
            self.meta = self.rfile.read(header["len_meta"])
            # print "meta is: \"%s\"" % meta

            #logging.debug("reading %i bytes of headers" % lengths[1])
            self.headers = self.rfile.read(header["len_headers"])
            # print "headers are: \"%s\"" % headers

            #logging.debug("reading %i bytes of body" % lengths[2])
            self.body = self.rfile.read(header["len_body"])
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
        self.vxid = header["vxid"]

        self.policy()


    def respond(self, rcode, respmeta, respheaders, respbody):
        if type(respmeta) == dict:
            respmeta = "\n".join(
                [ "%s: %s" % (x[0], x[1]) for x in respmeta.items()])

        if type(respheaders) == dict:
            respheaders = "\n".join(
                [ "%s: %s" % (x[0], x[1]) for x in respheaders.items()])

        header = "VPOL" + struct.pack("!HHQIIQ", 1, \
            rcode, self.vxid, len(respmeta), len(respheaders), len(respbody))

        logging.debug("sending header: %s" % str(header))
        self.request.send(header)

        self.request.send(respmeta)
        self.request.send(respheaders)
        self.request.send(respbody)

    def policy(self):
        """
            Override this with your application logic.
        """
        raise NotImplementedError()


class AllOKhandler(BaseVPOLRequestHandler):
    def policy(self):
        if 1:
            print "meta: ",
            pprint(self.meta)

            print "headers: ",
            pprint(self.headers),

            print "body: ",
            pprint(self.body)
        # let the policy daemon vouch for the client for a while. ttl, ip.
        #self.request.send("policy-whitelist-client: 3600,1.2.3.4\n")
        self.respond(200, {"close": "yes"}, {"foo": "bar"}, "new req body")
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

