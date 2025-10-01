#! /usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2025 Linaro Ltd.

import os, re, sys

def empty_data():
    return {'dirs': {}}

def verify_data(data):

    if data == empty_data():
        return True

    ret = True

    blocklineno = min(data['dirs'].values())

    for (entry, lineno) in data['dirs'].items():
        if not os.path.exists(entry):
            sys.stderr.write("WHENCE:%d: dir %s doesn't exist\n" % (lineno, entry))
            ret = False
        elif not os.path.isdir(entry):
            sys.stderr.write("WHENCE:%d: %s is not a directory\n" % (lineno, entry))
            ret = False
        elif entry.endswith("/"):
            sys.stderr.write("WHENCE:%d: stray ending '/' in %s\n" % (lineno, entry))
            ret = False

    if 'licence' in data:
        lic, lineno = data['licence']
        if not os.path.exists(lic):
            sys.stderr.write("WHENCE:%d: licence %s doesn't exist\n" % (lineno, lic))
            ret = False
        elif not os.path.isfile(lic):
            sys.stderr.write("WHENCE:%d: %s is not a file\n" % (lineno, lic))
            ret = False
    else:
        sys.stderr.write("WHENCE:%d: licence not specified\n" % blocklineno)
        ret = False

    if 'status' in data:
        status, lineno = data['status']
        if "Redistributable" not in status:
            sys.stderr.write("WHENCE:%d: binaries are not redistributable\n" % lineno)
            ret = False
    else:
        sys.stderr.write("WHENCE:%d: status not specified\n" % blocklineno)
        ret = False

    return ret

def load_whence():
    data = empty_data()

    with open("WHENCE", encoding="utf-8") as file:
        pattern_dir = re.compile("^Dir: (.*)\n$")
        pattern_licence = re.compile("^Licence: (.*)\n$")
        pattern_status = re.compile("^Status: (.*)\n$")
        pattern_break = re.compile("^----")

        for (lineno, line) in enumerate(file, start=1):
            match = pattern_dir.match(line)
            if match:
                data['dirs'][match.group(1)] = lineno
                continue

            match = pattern_licence.match(line)
            if match:
                data['licence'] = (match.group(1), lineno)

            match = pattern_status.match(line)
            if match:
                data['status'] = (match.group(1), lineno)

            match = pattern_break.match(line)
            if match:
                yield data
                data = empty_data()
                continue

    # return final data entry, might be empty
    yield data

def load_config():
    with open("config.txt", encoding="utf-8") as file:
        pattern_empty = re.compile("^#|^$")
        pattern_data = re.compile("Install: ([^ \t]+)[ \t]+([^ \t]+)[ \t]+([^ \t]+)\n")

        for (lineno, line) in enumerate(file, start=1):
            if pattern_empty.match(line):
                continue
            match = pattern_data.match(line)
            if match:
                yield (lineno, match.group(1), match.group(2), match.group(3))
                continue

            raise Exception("config.txt: %d: failed to parse '%s'" % (lineno, line[:-1]))

DSPS = [ "adsp", "cdsp", "sdsp", "cdsp1", "gdsp0", "gdsp1" ]

def check_config(data, dirs):
    (lineno, path, dsp, subdir) = data
    ret = True

    if path.endswith("/"):
        sys.stderr.write("config.txt: %d: trailing '/' in %s\n" % (lineno, path))
        ret = False

    if subdir.endswith("/"):
        sys.stderr.write("config.txt: %d: trailing '/' in %s\n" % (lineno, subdir))
        ret = False

    full = "%s/%s" % (path, subdir)
    if full not in dirs:
        sys.stderr.write("config.txt: %d: path '%s' not found in WHENCE\n" % (lineno, full))
        ret = False

    if dsp not in DSPS:
        sys.stderr.write("config.txt: %d: unknown DSP type '%s'\n" % (lineno, dsp))
        ret = False

    return ret

def list_git():
    if not os.path.exists(".git"):
        sys.stderr.write("Skipping git ls-files check, no .git dir")
        return None

    git = os.popen("git ls-files")
    for file in git:
        yield file.rstrip("\n")

    if git.close():
        sys.stderr.write("WHENCE: skipped contents validation, git file listing failed\n")

def main():
    okay = True
    dirs = {}
    licences = {'LICENSE.MIT' : None}

    for data in load_whence():
        if not verify_data(data):
            okay = False

        dirs.update(dict.fromkeys(data['dirs'].keys()))
        if 'licence' in data:
            licences[data['licence'][0]] = None

    known_files = ['config.txt', 'Makefile', 'TODO', 'README.md', 'WHENCE']

    for file in list_git():
        if os.path.dirname(file) in dirs:
            continue

        if file in licences:
            continue

        if os.path.dirname(file) == 'scripts':
            continue

        if os.path.dirname(file) == '.github/workflows':
            continue

        if file in known_files:
            continue

        sys.stderr.write("WHENCE: file %s is not under a listed directory\n" % file)
        okay = False

    try:
        for data in load_config():
            if not check_config(data, dirs):
                okay = False

    except Exception as e:
        sys.stderr.write("%s\n" % e)
        okay = False

    return 0 if okay else 1

if __name__ == "__main__":
    sys.exit(main())
