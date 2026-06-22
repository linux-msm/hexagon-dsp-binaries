#! /usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2025 Linaro Ltd.
#
# Validate WHENCE and config.txt file entries for consistency and completeness

import json, os, re, sys, yaml

import jsonschema

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
        pattern_install = re.compile("Install: ([^ \t]+)[ \t]+([^ \t]+)[ \t]+([^ \t]+)\n")
        pattern_link = re.compile("Link: ([^ \t]+)[ \t]+([^ \t]+)\n")

        for (lineno, line) in enumerate(file, start=1):
            if pattern_empty.match(line):
                continue

            match = pattern_install.match(line)
            if match:
                yield ("install", lineno, *match.groups())
                continue

            match = pattern_link.match(line)
            if match:
                yield ("link", lineno, *match.groups())
                continue

            raise Exception("config.txt: %d: failed to parse '%s'" % (lineno, line[:-1]))

DSPS = [ "adsp", "cdsp", "sdsp", "cdsp1", "gdsp0", "gdsp1" ]

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

def check_link_config(data):
    (lineno, src_path, dst_path) = data
    ret = True

    if src_path.endswith("/"):
        sys.stderr.write("config.txt: %d: trailing '/' in %s\n" % (lineno, src_path))
        ret = False

    if dst_path.endswith("/"):
        sys.stderr.write("config.txt: %d: trailing '/' in %s\n" % (lineno, dst_path))
        ret = False

    dsp_path = os.path.dirname(src_path)
    sourcedir = os.path.dirname(dsp_path)
    if not os.path.exists(sourcedir):
        sys.stderr.write("config.txt: %d: dir %s doesn't exist\n" % (lineno, sourcedir))
        ret = False

    if os.path.basename(dsp_path) != "dsp":
        sys.stderr.write("config.txt: %d: DSP type not under 'dsp' dir %s\n" % (lineno, src_path))
        ret = False

    return ret

def check_config(data, dirs):
    ret = True

    if data[0] == "install":
       ret = check_install_config(data[1:], dirs)
    elif data[0] == "link":
       ret = check_link_config(data[1:])

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

def check_conf_file_format(path):
    """Validate properties not visible to the YAML parser."""
    okay = True

    with open(path, "rb") as f:
        raw = f.read()

    if len(raw) == 0:
        sys.stderr.write(f"{path}: file is empty\n")
        return False

    if not raw.endswith(b"\n"):
        sys.stderr.write(
            f"{path}: missing trailing newline at end of file\n")
        okay = False
    elif raw.endswith(b"\n\n"):
        sys.stderr.write(
            f"{path}: trailing blank line(s) at end of file\n")
        okay = False

    first_line = raw.split(b"\n", 1)[0].decode("utf-8", errors="replace")
    SPDX_HEADER_RE = re.compile(r"^# SPDX-License-Identifier: [^\s]+\s*$")
    if not SPDX_HEADER_RE.match(first_line):
        sys.stderr.write(
            f"{path}: missing SPDX-License-Identifier header on first"
            f" line\n")
        okay = False

    return okay

def load_schema():
    with open("conf.d/schema.json", encoding="utf-8") as file:
        return json.load(file)

def check_conf_against_schema(path, data, validator):
    """Validate YAML contents against conf.d/schema.json."""
    okay = True
    for err in sorted(validator.iter_errors(data), key=lambda e: e.path):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        sys.stderr.write(f"{path}: {loc}: {err.message}\n")
        okay = False
    return okay

def load_machine_dsp_paths():
    """Validate and parse conf.d/*.yaml files; return the set of base paths."""
    paths = set()
    okay = True

    validator = jsonschema.Draft202012Validator(load_schema())

    for conf in sorted(os.listdir("conf.d")):
        if conf == "schema.json":
            continue
        if not conf.endswith(".yaml"):
            sys.stderr.write(
                f"conf.d/{conf}: unexpected non-yaml file\n")
            okay = False
            continue

        full = os.path.join("conf.d", conf)

        if not check_conf_file_format(full):
            okay = False

        try:
            with open(full, encoding="utf-8") as file:
                data = yaml.safe_load(file)
        except yaml.YAMLError as e:
            sys.stderr.write(f"{full}: YAML parse error: {e}\n")
            okay = False
            continue

        if not check_conf_against_schema(full, data, validator):
            okay = False
            continue

        # Extract base paths (without /dsp suffix) from DSP_LIBRARY_PATH
        for machine_name, machine_data in data['machines'].items():
            dsp_path = machine_data['DSP_LIBRARY_PATH']
            base_path = dsp_path[:-len('/dsp')]
            paths.add(base_path)

            suffix = base_path[base_path.find('/') + 1:]
            name = "hexagon-dsp-binaries-%s.yaml" % \
                suffix.lower().replace('/', '-')
            if name != conf:
                sys.stderr.write(
                    f"Name mismatch, {conf} should be named {name}\n")
                okay = False

    return paths if okay else None

def check_config_against_machine_paths(config_data, machine_paths):
    """Check that config.txt paths are consistent with configuration YAML files."""
    if machine_paths is None:
        return True

    ret = True
    reported_paths = set()  # Track paths we've already reported as missing

    for data in config_data:
        if data[0] == "install":
            (lineno, path, dsp, subdir) = data[1:]
            if path not in machine_paths and path not in reported_paths:
                sys.stderr.write("config.txt: %d: Install path '%s' not found in YAML configs\n" % (lineno, path))
                reported_paths.add(path)
                ret = False
        elif data[0] == "link":
            (lineno, src_path, dst_path) = data[1:]
            # Extract base path from link target (dst_path)
            # Link format: path/to/device/dsp/dsptype
            parts = dst_path.split('/')
            if len(parts) >= 2 and parts[-2] == 'dsp':
                base_path = '/'.join(parts[:-2])
                if base_path not in machine_paths and base_path not in reported_paths:
                    sys.stderr.write("config.txt: %d: Link target base path '%s' not found in YAML configs\n" % (lineno, base_path))
                    reported_paths.add(base_path)
                    ret = False

    return ret

def check_dir(subdir):
    pattern_shell = re.compile("^fastrpc_shell(_unsigned)?_[0-9]$")
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

    for data in load_whence():
        if not verify_data(data):
            okay = False

        dirs.update(dict.fromkeys(data['dirs'].keys()))
        if 'licence' in data:
            licences[data['licence'][0]] = None

    known_files = ['.gitignore', 'config.txt', 'Makefile', 'TODO', 'README.md', 'WHENCE']

    for file in list_git():
        if os.path.dirname(file) == "conf.d" and \
                (os.path.basename(file).endswith(".yaml") or
                 os.path.basename(file) == "schema.json"):
            continue

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

    # Load 00-hexagon-dsp-binaries.yaml for consistency checking
    machine_paths = load_machine_dsp_paths()
    if not machine_paths:
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

    # Check config.txt paths against 00-hexagon-dsp-binaries.yaml
    if not check_config_against_machine_paths(config_data, machine_paths):
        okay = False

    for entry in dirs.keys():
        if not check_dir(entry):
            sys.stderr.write("WHENCE: subdir %s failed the checks\n" % entry)
            okay = False

    return 0 if okay else 1

if __name__ == "__main__":
    sys.exit(main())
