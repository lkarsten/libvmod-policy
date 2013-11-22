============
vmod_policy
============

----------------------
Varnish policy daemons
----------------------

:Author: Lasse Karstensen
:Date: 2013-11-18
:Version: 1.0
:Manual section: 3

SYNOPSIS
========

import policy;

DESCRIPTION
===========

The policy vmod allows request policy handling to be done in a separate
process.

The goal of this is to simplify the development of advanced decision
policies for Varnish.

A policy daemon will be supplied with:

* Metainfo; client IP/port, URI, etc.
* Request headers
* Request body (in 4.0, empty in 3.0)


Example usage can be:

* Request rate limiting (number, size, etc)
* DNS blacklists for expensive POST requests.
* Client profiling/tracking


See the vpol-protocol.txt for a description of the line protocol between
libvmod-policy and the policy daemon.


FUNCTIONS
=========

check
-----

Prototype
        ::

                check(STRING S)
Return value
	STRING
Description
	Checks with policy server in S, and returns the string provided by it.
Example
        ::

                if (policy.check("127.0.0.1:15696") == 400) {
                    error 403 "Forbidden";
                }

INSTALLATION
============

This is an example skeleton for developing out-of-tree Varnish
vmods available from the 3.0 release. It implements the "Hello, World!" 
as a vmod callback. Not particularly useful in good hello world 
tradition,but demonstrates how to get the glue around a vmod working.

The source tree is based on autotools to configure the building, and
does also have the necessary bits in place to do functional unit tests
using the varnishtest tool.

Usage::

 ./configure VARNISHSRC=DIR [VMODDIR=DIR]

`VARNISHSRC` is the directory of the Varnish source tree for which to
compile your vmod. Both the `VARNISHSRC` and `VARNISHSRC/include`
will be added to the include search paths for your module.

Optionally you can also set the vmod install directory by adding
`VMODDIR=DIR` (defaults to the pkg-config discovered directory from your
Varnish installation).

Make targets:

* make - builds the vmod
* make install - installs your vmod in `VMODDIR`
* make check - runs the unit tests in ``src/tests/*.vtc``



COPYRIGHT
=========

This document is licensed under the same license as the
libvmod-policy project. See LICENSE for details.

* Copyright (c) 2013 Varnish Software
