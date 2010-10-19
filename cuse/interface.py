# -*- coding: utf-8 -*-
'''
Copyright (c) 2010, Naranjo Manuel Francisco <manuel@aircable.net>
Copyright (c) 2010, Nikolaus Rath <Nikolaus@rath.org>
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the main author nor the names of other contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


This module defines the interface between the CUSE C and Python API.

Note that all "string-like" quantities (e.g. file names, extended attribute names & values) are
represented as bytes, since POSIX doesn't require any of them to be valid unicode strings.
'''

# Since we are using ctype Structures, we often have to
# access attributes that are not defined in __init__
# (since they are defined in _fields_ instead)
#pylint: disable-msg=W0212

# We need globals
#pylint: disable-msg=W0603

from __future__ import division, print_function, absolute_import

# Using .. as libfuse makes PyDev really unhappy.
from . import cuse_api
libcuse = cuse_api

from . import ioctl_api
ioctl = ioctl_api

from ctypes import c_char_p, sizeof, create_string_buffer, addressof, string_at, POINTER, c_char, cast
from functools import partial
import errno
import logging
import sys
import os


__all__ = [ 'ENOATTR', 'ENOTSUP', 'close',
            'fuse_version', 'init', 'main', 'ioctl_dict' ]


# These should really be defined in the errno module, but
# unfortunately they are missing
ENOATTR = libcuse.ENOATTR
ENOTSUP = libcuse.ENOTSUP

log = logging.getLogger("cuse")
logging.basicConfig(level=logging.DEBUG)

# Init globals
operations = None
cuse_ops = None
session = None
channel = None

def fuse_version():
    '''Return version of loaded fuse library'''

    return libcuse.fuse_version()

def init(operations_, devname, args, major=231, minor=1):
    '''Initialize a CUSE device'''

    def pointer_devname(devname):
      a=cast(c_char_p("DEVNAME=%s" % devname), POINTER(c_char))
      return POINTER(POINTER(c_char))(a)

    cuse_name="/dev/cuse"
    log.debug('Initializing llfuse in cuse mode')

    global operations
    global cuse_ops
    global session
    global channel

    operations = operations_
    cuse_ops = libcuse.cuse_lowlevel_ops()
    cuse_info = libcuse.cuse_info()
    cuse_args = make_cuse_args(args)

    cuse_info.dev_major = major
    cuse_info.dev_minor = minor
    cuse_info.dev_info_argc = 1
    cuse_info.dev_info_argv = pointer_devname(devname)
    cuse_info.flags = libcuse.CUSE_UNRESTRICTED_IOCTL

    # make sure fd 0,1 and 2 are open to avoid chaos
    while True:
	fd = open("/dev/null", "rw")
	if fd.fileno()>2:
	    fd.close()
	    break

    # Init cuse_ops
    module = globals()
    for (name, prototype) in libcuse.cuse_lowlevel_ops._fields_:
        if hasattr(operations, name):
	    log.debug("provides %s function", name)
            setattr(cuse_ops, name, prototype(getattr(operations, name)))

    log.debug('Calling cuse_lowlevel_new')
    session = libcuse.cuse_lowlevel_new(cuse_args, cuse_info, cuse_ops, None)
    if not session:
        raise RuntimeError("cuse_lowlevel_new() failed")

    try:
      cuse=os.open(cuse_name, os.O_RDWR)
    except IOError, err:
	if err.errno in [errno.ENODEV, errno.ENOENT]:
	    log.info("fuse: device not found, try 'modprobe cuse'")
	else:
	    log.info("fuse: failed to open %s: %s" % (cuse_name,
		os.strerror(err.errno)))
	log.debug('Calling cuse_session_destroy')
	libcuse.fuse_session_destroy(session)
	raise

    try:
      ch = libcuse.fuse_kern_chan_new(cuse)
      log.debug("got kern chan %s for fd %s" % (repr(ch), cuse))
      log.debug("%s" % libcuse.fuse_chan_fd(ch))
    except Exception, err:
      log.error(err)
      libcuse.fuse_session_destroy(session)
      raise

    log.debug("adding channel to session")
    libcuse.fuse_session_add_chan(session, ch)

    if libcuse.fuse_set_signal_handlers(session) == -1:
      libcuse.fuse_session_destroy(session)
      raise RuntimeError("fuse_set_signal_handlers() failed")

#    if libcuse.fuse_daemonize(1) == -1:
#      libcuse.fuse_session_destroy(session)
#      raise RuntimeError("Failed to set to foreground")

    log.debug("everything setup for cuse!")
    return

def make_cuse_args(args):
    '''
    Create cuse_args Structure for CUSE driver, you send parameters to CUSE
    this way
    '''

    args1 = [ sys.argv[0] ]
    for opt in args:
        args1.append(b'-o')
        args1.append(opt)

    # Init fuse_args struct
    fuse_args = libcuse.fuse_args()
    fuse_args.allocated = 0
    fuse_args.argc = len(args1)
    fuse_args.argv = (POINTER(c_char) * len(args1))(*[cast(c_char_p(x), POINTER(c_char))
                                                      for x in args1])
    return fuse_args


def main(single=False):
    '''Run CUSE main loop'''

    if not session:
        raise RuntimeError('Need to call init() before main()')

    if single:
        log.debug('Calling fuse_session_loop')
        if libcuse.fuse_session_loop(session) != 0:
            raise RuntimeError("fuse_session_loop() failed")
    else:
        log.debug('Calling fuse_session_loop_mt')
        if libcuse.fuse_session_loop_mt(session) != 0:
            raise RuntimeError("fuse_session_loop_mt() failed")


def close():
    '''Clean up CUSE'''

    global operations
    global cuse_ops
    global session
    global channel

    log.debug('Calling fuse_session_remove_chan')
    libcuse.fuse_session_remove_chan(channel)
    log.debug('Calling fuse_remove_signal_handlers')
    libcuse.fuse_remove_signal_handlers(session)
    log.debug('Calling fuse_session_destroy')
    libcuse.fuse_session_destroy(session)

    operations = None
    cuse_ops = None
    session = None
    channel = None

def __ioctl_symbols():
    out={}
    for k in dir(ioctl):
	if not k.startswith('_') and type(getattr(ioctl, k, None)) is int:
	    out[getattr(ioctl, k)]=k
    return out

ioctl_dict = __ioctl_symbols()
