#! /usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
#
# Check firmware version strings in binaries against linux-firmware repo

import glob
import hashlib
import os
import re
import struct
import sys
import subprocess

from check import load_config

# Print warnings about ignored hash mismatches only when V is set non-empty.
VERBOSE = bool(os.environ.get('V'))

def segment_hashes(data):
    """Return the per-segment SHA-256 digests of a Hexagon ELF, or None.

    The signed DSP firmware authorises each Hexagon binary by storing, in
    program-header order, the SHA-256 digest of every ELF segment (computed
    over its on-disk bytes, p_offset .. p_offset + p_filesz).
    """
    # little-endian 32-bit ELF only (EI_CLASS, EI_DATA)
    if data[:4] != b'\x7fELF' or data[4] != 1 or data[5] != 1:
        return None

    e_phoff = struct.unpack_from('<I', data, 28)[0]
    e_phentsize = struct.unpack_from('<H', data, 42)[0]
    e_phnum = struct.unpack_from('<H', data, 44)[0]

    hashes = []
    for i in range(e_phnum):
        base = e_phoff + i * e_phentsize
        p_offset = struct.unpack_from('<I', data, base + 4)[0]
        p_filesz = struct.unpack_from('<I', data, base + 16)[0]
        hashes.append(hashlib.sha256(data[p_offset:p_offset + p_filesz]).digest())

    return hashes

def load_hashes_ignore(bindir):
    """Return the set of filenames whose hash mismatch should be ignored.

    A binary version directory may carry a 'hashes-ignore.txt' listing files
    (one per line, '#' comments allowed) that are known not to match the
    firmware, e.g. when Qualcomm shipped rebuilt binaries under an unchanged
    QC_IMAGE_VERSION_STRING.
    """
    ignore = set()
    path = os.path.join(bindir, "hashes-ignore.txt")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                name = line.split('#', 1)[0].strip()
                if name:
                    ignore.add(name)
    return ignore

def check_hashes(fwfile, bindir):
    """Verify every Hexagon binary in bindir is authorised by fwfile.

    The firmware stores each binary's segment digests contiguously, so a binary
    is authorised iff the concatenation of its digests appears in the image.
    Files listed in the directory's hashes-ignore.txt are exempt. Returns True
    if all non-ignored binaries are present, printing the ones that are not.
    """
    okay = True

    if not os.path.isdir(bindir):
        return True

    ignore = load_hashes_ignore(bindir)

    with open(fwfile, 'rb') as f:
        blob = f.read()

    for file in sorted(os.listdir(bindir)):
        path = os.path.join(bindir, file)
        if not os.path.isfile(path):
            continue

        with open(path, 'rb') as f:
            hashes = segment_hashes(f.read())
        if hashes is None:
            continue

        if blob.find(b''.join(hashes)) < 0:
            if file in ignore:
                if VERBOSE:
                    print("warning: ignoring hash mismatch %s (listed in hashes-ignore.txt)" % path)
            else:
                print("hash mismatch %s not authorised by %s" % (path, fwfile))
                okay = False

    return okay

def get_ver(file):
    pattern_ver = re.compile("^QC_IMAGE_VERSION_STRING=(.*)$")
    result = subprocess.run(['strings', file], stdout=subprocess.PIPE)

    for line in result.stdout.decode('utf-8').split('\n'):
        match = pattern_ver.match(line)
        if match:
            return match.group(1)

    return None


def load_fws(qcompath):
    result = {}
    prefix = os.path.join(qcompath, "")
    pattern_dsp = re.compile("(qc)?((.*dsp[0-9]?|slpi)([0-9][0-9[0-9]][0-9])?).mbn$")

    for subdir in os.walk(qcompath):
        for file in subdir[2]:
            if 'dtb' in file:
                continue

            match = pattern_dsp.match(file)
            if not match:
                continue

            subpath = subdir[0].removeprefix(prefix)
            dsp = match.group(2)
            if dsp == "slpi":
                dsp = "sdsp"
            elif dsp == "cdsp0":
                dsp = "cdsp"
            elif dsp.startswith("gp"):
                dsp = 'g' + dsp[2:]
            name = os.path.join(subpath, dsp)
            version = get_ver(os.path.join(subdir[0], file))
            result[name] = {'version': version, 'filename': os.path.join(subpath, file), 'seen': False}

            #print("%s %s %s" % (name, version, result[name]['filename']))

    return result

def main():
    if len(sys.argv) != 2:
        print("Usage: %s <path-to-linux-firmware>" % sys.argv[0])
        return 1

    fwpath = sys.argv[1]
    qcompath = os.path.join(fwpath, "qcom")
    fws = load_fws(qcompath)

    okay = True

    for data in load_config():
        if data[0] != "install":
            continue

        soc = data[2].split('/')[0]
        path = os.path.join(data[2], data[3])
        socpath = os.path.join(soc, data[3])
        version = data[4].removeprefix("%s-" % data[3])
        bindir = os.path.join(data[2], data[4])

        mismatch = None

        if socpath in fws:
            if fws[socpath]['version'] == version:
                fws[socpath]['seen'] = True
                #print("seen %s" % socpath)
                fwfile = os.path.join(qcompath, fws[socpath]['filename'])
                okay = check_hashes(fwfile, bindir) and okay
                continue
            mismatch = f"version mismatch %s %s vs %s %s" % (path, version, fws[socpath]['filename'], fws[socpath]['version'])

        if path in fws:
            if fws[path]['version'] == version:
                fws[path]['seen'] = True
                #print("seen %s" % path)
                fwfile = os.path.join(qcompath, fws[path]['filename'])
                okay = check_hashes(fwfile, bindir) and okay
                continue
            mismatch = f"version mismatch %s %s vs %s %s" % (path, version, fws[path]['filename'], fws[path]['version'])

        if mismatch:
            print(mismatch)
        else:
            print("no match for DSP binaries", path, "version", version)

    for data in fws.values():
        if not data['seen']:
            print("no match for DSP firmware", data["filename"], "version", data["version"])

    return 0 if okay else 1

if __name__ == "__main__":
    sys.exit(main())
