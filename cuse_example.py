#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
$Id: llfuse_example.py 46 2010-01-29 17:10:10Z nikratio $

Copyright (c) 2010, Nikolaus Rath <Nikolaus@rath.org>
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the main author nor the names of other contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
''' 

from __future__ import division, print_function, absolute_import

import cuse, errno, stat, sys
from cuse import cuse_api as libcuse
from cuse.interface import ioctl_dict

class Device():
  '''A very simple example filesystem'''
  flag = False
  input_buffer=""

  def open(self, req, file_info):
    print ("open %s %s" %(req, file_info))
    libcuse.fuse_reply_open(req, file_info)
    self.flag = False

  def write(self, req, buf, length, offset, file_info):
    print ("write %s %s %s %s" %(req, buf, length, offset))
    self.input_buffer+=buf[offset:length]
    print (self.input_buffer)
    libcuse.fuse_reply_write(req, length)

  def read(self, req, size, off, file_info):
    out = self.input_buffer[off:size]
    print ("read size: %s off: %s reply: %s buffer: %s" % (
      size, off, len(out), len(self.input_buffer)))
    libcuse.fuse_reply_buf(req, self.input_buffer[off:size], len(out))
    self.input_buffer=self.input_buffer[off+size+1:]

  def ioctl(self, req, cmd, arg_p, file_info, uflags, in_buff_p,
							in_bufsz, out_bufsz):
    print ("ioctl %s" % ioctl_dict[cmd])
    libcuse.fuse_reply_ioctl(req, 0, None, 0);


if __name__ == '__main__':
    
    if len(sys.argv) < 2:
        raise SystemExit('Usage: %s <devname>' % sys.argv[0])
    
    devname = sys.argv[1]
    operations = Device()
    
    cuse.init(operations, devname, sys.argv[2:])
    try:
	cuse.main(True)
    except Exception, err:
	print ("CUSE main ended %s" % str(err))
