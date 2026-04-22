#! /usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
#
# Check firmware version strings in binaries against linux-firmware repo

import glob
import os
import re
import sys
import subprocess

from check import load_config

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

    for data in load_config():
        if data[0] != "install":
            continue

        soc = data[2].split('/')[0]
        path = os.path.join(data[2], data[3])
        socpath = os.path.join(soc, data[3])
        version = data[4].removeprefix("%s-" % data[3])

        mismatch = None

        if socpath in fws:
            if fws[socpath]['version'] == version:
                fws[socpath]['seen'] = True
                #print("seen %s" % socpath)
                continue
            mismatch = f"version mismatch %s %s vs %s %s" % (path, version, fws[socpath]['filename'], fws[socpath]['version'])

        if path in fws:
            if fws[path]['version'] == version:
                fws[path]['seen'] = True
                #print("seen %s" % path)
                continue
            mismatch = f"version mismatch %s %s vs %s %s" % (path, version, fws[path]['filename'], fws[path]['version'])

        if mismatch:
            print(mismatch)
        else:
            print("no match for DSP binaries", path, "version", version)

    for data in fws.values():
        if not data['seen']:
            print("no match for DSP firmware", data["filename"], "version", data["version"])

if __name__ == "__main__":
    sys.exit(main())
