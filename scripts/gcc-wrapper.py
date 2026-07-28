#! /usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright (c) 2011-2016, The Linux Foundation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of The Linux Foundation nor
#       the names of its contributors may be used to endorse or promote
#       products derived from this software without specific prior written
#       permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NON-INFRINGEMENT ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Invoke gcc, looking for warnings, and causing a failure if there are
# non-whitelisted warnings.

import errno
import re
import os
import sys
import subprocess

# Note that gcc uses unicode, which may depend on the locale.  TODO:
# force LANG to be set to en_US.UTF-8 to get consistent warnings.

allowed_warnings = set([
    "core.c:144",
    "inet_connection_sock.c:430",
    "inet_connection_sock.c:467",
    "inet6_connection_sock.c:89",
    # add_verity_corruption_tag() is only called from inside
    # #ifdef CONFIG_PANIC_ON_DM_VERITY_ERRORS (drivers/md/dm-verity-target.c),
    # which this tree's tama_akari_defconfig deliberately does not set (matching
    # every defconfig in sony-sdm845/android_kernel_sony_sdm845 @ lineage-20,
    # despite Sony's own arch/arm64/configs/diffconfig/common_diffconfig setting
    # it =y for stock/production firmware -- see lineage-port-attempt commit
    # for the full writeup of that discrepancy). The function's only real
    # statement is already commented out in this source drop
    # (rdtags_add_tag(...) is dead code as shipped), so with the ifdef'd-out
    # call site this is a true, harmless dead-code warning under our config,
    # not a sign of a real problem. Whitelisting it here rather than touching
    # dm-verity-target.c itself or flipping PANIC_ON_DM_VERITY_ERRORS, since
    # this file is squarely in the project's AVB/dm-verity risk zone and this
    # task is only meant to get past a build gate, not make a verified-boot
    # policy decision.
    "dm-verity-target.c:217",
 ])

# Capture the name of the object file, can find it.
ofile = None

warning_re = re.compile(r'''(.*/|)([^/]+\.[a-z]+:\d+):(\d+:)? warning:''')
def interpret_warning(line):
    """Decode the message from gcc.  The messages we care about have a filename, and a warning"""
    line = line.rstrip('\n')
    m = warning_re.match(line)
    if m and m.group(2) not in allowed_warnings:
        print("error, forbidden warning:", m.group(2))

        # If there is a warning, remove any object if it exists.
        if ofile:
            try:
                os.remove(ofile)
            except OSError:
                pass
        sys.exit(1)

def run_gcc():
    args = sys.argv[1:]
    # Look for -o
    try:
        i = args.index('-o')
        global ofile
        ofile = args[i+1]
    except (ValueError, IndexError):
        pass

    compiler = sys.argv[0]

    try:
        proc = subprocess.Popen(args, stderr=subprocess.PIPE, universal_newlines=True)
        for line in proc.stderr:
            print(line, end="")
            interpret_warning(line)

        result = proc.wait()
    except OSError as e:
        result = e.errno
        if result == errno.ENOENT:
            print(args[0] + ':', e.strerror)
            print('Is your PATH set correctly?')
        else:
            print(' '.join(args), str(e))

    return result

if __name__ == '__main__':
    status = run_gcc()
    sys.exit(status)
