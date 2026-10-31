#! /usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2025 Linaro Ltd.
#
# Validate WHENCE and config.txt file entries for consistency and completeness

import json, os, re, sys

import jsonschema

def empty_data():
    return {'dirs': {}}

def verify_data(data):

    if data == empty_data():
        return True

    ret = True

    blocklineno = min(data['dirs'].values())

    prev = None
    for (entry, lineno) in data['dirs'].items():
        if prev is not None and entry < prev:
            sys.stderr.write("WHENCE:%d: dir %s is not sorted, should come before %s\n" % (lineno, entry, prev))
            ret = False
        prev = entry

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
        pattern_install = re.compile("Install: ([^ \t]+)[ \t]+([^ \t]+)[ \t]+([^ \t]+)\n")
        pattern_reuse = re.compile("Reuse: ([^ \t]+)[ \t]+([^ \t]+)[ \t]+([^ \t]+)\n")
        pattern_machine = re.compile("Machine: ([^ \t]+)[ \t]+([^\t\n]*[^ \t\n])\n")
        pattern_arch = re.compile("Arch: ([^ \t]+)[ \t]+([^ \t]+)[ \t]+([^ \t]+)\n")

        for (lineno, line) in enumerate(file, start=1):
            if pattern_empty.match(line):
                continue

            match = pattern_install.match(line)
            if match:
                yield ("install", lineno, *match.groups())
                continue

            match = pattern_reuse.match(line)
            if match:
                yield ("reuse", lineno, *match.groups())
                continue

            match = pattern_machine.match(line)
            if match:
                yield ("machine", lineno, *match.groups())
                continue

            match = pattern_arch.match(line)
            if match:
                yield ("arch", lineno, *match.groups())
                continue

            raise Exception("config.txt: %d: failed to parse '%s'" % (lineno, line[:-1]))

DSPS = [ "adsp", "adsp1", "cdsp", "sdsp", "cdsp1", "gdsp0", "gdsp1" ]
ARCH_DSPS = [ "adsp", "cdsp", "mdsp", "sdsp" ]

def check_install_config(data, dirs):
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

def check_reuse_config(data):
    (lineno, path, dsp, source) = data
    ret = True

    if path.endswith("/"):
        sys.stderr.write("config.txt: %d: trailing '/' in %s\n" % (lineno, path))
        ret = False

    if source.endswith("/"):
        sys.stderr.write("config.txt: %d: trailing '/' in %s\n" % (lineno, source))
        ret = False

    if dsp not in DSPS:
        sys.stderr.write("config.txt: %d: unknown DSP type '%s'\n" % (lineno, dsp))
        ret = False

    return ret

def check_machine_config(data):
    (lineno, path, name) = data
    ret = True

    if path.endswith("/"):
        sys.stderr.write("config.txt: %d: trailing '/' in %s\n" % (lineno, path))
        ret = False

    # machine names are written to YAML files as double-quoted strings
    if '"' in name or '\\' in name:
        sys.stderr.write("config.txt: %d: unsupported character in machine name '%s'\n" % (lineno, name))
        ret = False

    return ret

def check_arch_config(data):
    (lineno, path, dsp, arch) = data
    ret = True

    if path.endswith("/"):
        sys.stderr.write("config.txt: %d: trailing '/' in %s\n" % (lineno, path))
        ret = False

    if dsp not in ARCH_DSPS:
        sys.stderr.write("config.txt: %d: unsupported DSP type '%s' for Arch:\n" % (lineno, dsp))
        ret = False

    return ret

def check_config(data, dirs):
    ret = True

    if data[0] == "install":
       ret = check_install_config(data[1:], dirs)
    elif data[0] == "reuse":
       ret = check_reuse_config(data[1:])
    elif data[0] == "machine":
       ret = check_machine_config(data[1:])
    elif data[0] == "arch":
       ret = check_arch_config(data[1:])

    return ret

def list_git():
    if not os.path.exists(".git"):
        sys.stderr.write("Skipping git ls-files check, no .git dir\n")
        return None

    git = os.popen("git ls-files")
    for file in git:
        yield file.rstrip("\n")

    if git.close():
        sys.stderr.write("WHENCE: skipped contents validation, git file listing failed\n")

def load_schema():
    with open("schema.json", encoding="utf-8") as file:
        return json.load(file)

def check_conf_against_schema(path, data, validator):
    """Validate the target configuration against schema.json."""
    okay = True
    for err in sorted(validator.iter_errors(data), key=lambda e: e.path):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        sys.stderr.write(f"{path}: {loc}: {err.message}\n")
        okay = False
    return okay

def config_key(data):
    """Sort key of a config.txt entry.

    Entries are sorted by board. For each board the Machine: entries come
    first, followed by the Arch: ones and then by Install: and Reuse: ones,
    each sorted by DSP.
    """
    if data[0] == "machine":
        return (data[2], 0, "")
    if data[0] == "arch":
        return (data[2], 1, data[3])
    return (data[2], 2, data[3])

def check_config_sorted(config_data):
    """Check that config.txt entries are sorted by board and DSP."""
    ret = True
    prev = None
    for data in config_data:
        if prev is not None and config_key(data) < config_key(prev):
            sys.stderr.write("config.txt: %d: entry for %s is not sorted, should come before line %d\n" % (data[1], data[2], prev[1]))
            ret = False
        prev = data

    return ret

def config_machines(config_data):
    """Return the target configuration described by config.txt.

    The configuration is returned as a dict mapping each board to the
    contents of its conf.d YAML file.
    """
    boards = {}
    for data in config_data:
        if data[0] == "machine":
            (lineno, path, name) = data[1:]
            boards.setdefault(path, {'machines': {}})['machines'][name] = \
                {'DSP_LIBRARY_PATH': "%s/dsp" % path}

    for data in config_data:
        if data[0] == "arch":
            (lineno, path, dsp, arch) = data[1:]
            for machine in boards.get(path, {'machines': {}})['machines'].values():
                machine["%s_ARCH" % dsp.upper()] = arch

    return boards

def check_config_machines(config_data):
    """Check Machine: and Arch: entries; return the set of their boards."""
    ret = True
    names = {}
    archs = set()

    for data in config_data:
        if data[0] == "machine":
            (lineno, path, name) = data[1:]
            if name in names:
                sys.stderr.write("config.txt: %d: machine '%s' is already described on line %d\n" % (lineno, name, names[name]))
                ret = False
            names[name] = lineno

    boards = config_machines(config_data)

    for data in config_data:
        if data[0] == "arch":
            (lineno, path, dsp, arch) = data[1:]
            if path not in boards:
                sys.stderr.write("config.txt: %d: Arch: entry for %s without Machine: entries\n" % (lineno, path))
                ret = False
            if (path, dsp) in archs:
                sys.stderr.write("config.txt: %d: duplicate Arch: entry for %s of %s\n" % (lineno, dsp, path))
                ret = False
            archs.add((path, dsp))

    validator = jsonschema.Draft202012Validator(load_schema())
    for (path, conf) in boards.items():
        if not check_conf_against_schema("config.txt: %s" % path, conf, validator):
            ret = False

    return set(boards) if ret else None

def check_reuse_installed(config_data):
    """Check that every Reuse: source is installed by an Install: line."""
    installed = set()
    for data in config_data:
        if data[0] == "install":
            (lineno, path, dsp, subdir) = data[1:]
            installed.add("%s/dsp/%s" % (path, dsp))

    ret = True
    for data in config_data:
        if data[0] == "reuse":
            (lineno, path, dsp, source) = data[1:]
            if "%s/dsp/%s" % (source, dsp) not in installed:
                sys.stderr.write("config.txt: %d: %s of %s is not installed\n" % (lineno, dsp, source))
                ret = False

    return ret

def check_config_against_machine_paths(config_data, machine_paths):
    """Check that every board configured in config.txt has Machine: entries."""
    if machine_paths is None:
        return True

    ret = True
    reported_paths = set()  # Track paths we've already reported as missing

    for data in config_data:
        if data[0] == "install":
            (lineno, path, dsp, subdir) = data[1:]
            if path not in machine_paths and path not in reported_paths:
                sys.stderr.write("config.txt: %d: Install path '%s' has no Machine: entries\n" % (lineno, path))
                reported_paths.add(path)
                ret = False
        elif data[0] == "reuse":
            (lineno, path, dsp, source) = data[1:]
            if path not in machine_paths and path not in reported_paths:
                sys.stderr.write("config.txt: %d: Reuse path '%s' has no Machine: entries\n" % (lineno, path))
                reported_paths.add(path)
                ret = False

    return ret

def check_dir(subdir):
    pattern_shell = re.compile(r"^fastrpc_shell(_unsigned)?(_[0-9])?$")
    pattern_library = re.compile("^[-_+0-9a-zA-Z]*\\.so(\\.[0-9]*)?$")

    okay = True

    # We alrady warned earlier
    if not os.path.exists(subdir):
        return False

    for file in os.listdir(subdir):
        fullname = os.path.join(subdir, file)

        if not os.path.isfile(fullname):
            sys.stderr.write("WHENCE: not a file %s\n" % fullname)
            okay = False

        # Optional list of binaries exempt from the firmware hash check.
        if file == "hashes-ignore.txt":
            continue

        if not pattern_shell.match(file) and \
           not pattern_library.match(file):
               sys.stderr.write("WHENCE: unknown file type %s\n" % fullname)
               okay = False

    return okay

def main():
    okay = True
    dirs = {}
    licences = {'LICENSE.MIT' : None}

    prev = None
    for data in load_whence():
        if not verify_data(data):
            okay = False

        if data['dirs']:
            (first, lineno) = next(iter(data['dirs'].items()))
            if prev is not None and first < prev:
                sys.stderr.write("WHENCE:%d: block for %s is not sorted, should come before %s\n" % (lineno, first, prev))
                okay = False
            prev = first

        dirs.update(dict.fromkeys(data['dirs'].keys()))
        if 'licence' in data:
            licences[data['licence'][0]] = None

    known_files = ['.gitignore', 'config.txt', 'Makefile', 'TODO', 'README.md', 'WHENCE', 'schema.json']

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

    # Collect config data for consistency check
    config_data = []
    try:
        for data in load_config():
            config_data.append(data)
            if not check_config(data, dirs):
                okay = False

    except Exception as e:
        sys.stderr.write("%s\n" % e)
        okay = False

    # The target configuration is generated from Machine: and Arch: entries
    machine_paths = check_config_machines(config_data)
    if machine_paths is None:
        okay = False

    if not check_config_against_machine_paths(config_data, machine_paths):
        okay = False

    if not check_reuse_installed(config_data):
        okay = False

    if not check_config_sorted(config_data):
        okay = False

    for entry in dirs.keys():
        if not check_dir(entry):
            sys.stderr.write("WHENCE: subdir %s failed the checks\n" % entry)
            okay = False

    return 0 if okay else 1

if __name__ == "__main__":
    sys.exit(main())
