#! /usr/bin/python3

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

def list_git():
    git = os.popen("git ls-files")
    for file in git:
        yield file.rstrip("\n")

    if git.close():
        sys.stderr.write("WHENCE: skipped contents validation, git file listing failed\n")

def main():
    okay = True
    dirs = {}
    licences = {}

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

    return 0 if okay else 1

if __name__ == "__main__":
    sys.exit(main())
