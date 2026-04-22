#! /usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Linaro Ltd.
#
# Filter WHENCE entries to only those referenced by a config file

import os, re, sys

def load_config(cfg):
    with open(cfg, encoding="utf-8") as config:
        pattern_inst = re.compile("^Install: ([^ \t]+)[ \t]+([^ \t]+)[ \t]+([^ \t]+)\n$")
        for line in config:
            match = pattern_inst.match(line)
            if match:
                yield os.path.join(match.group(1), match.group(3))

def filter_whence(whence, cfg):
    with open(whence, encoding="utf-8") as file:
        pattern_dir = re.compile("^Dir: (.*)\n$")
        pattern_break = re.compile("^----")
        matched = True # output file header until the first section

        for line in file:
            match = pattern_dir.match(line)
            if match:
                if match.group(1) in cfg:
                    matched = True
                    yield line
                continue

            match = pattern_break.match(line)
            if match:
                if matched:
                    matched = False
                    yield line
                    yield "\n"
                continue

            if matched:
                yield line


def main(args):
    if len(args) != 4:
        print("Usage: %s config.txt WHENCE OUT" % args[0])

    cfg = dict.fromkeys(load_config(args[1]))

    with open(args[3], mode="wt", encoding="utf-8") as out:
        for line in filter_whence(args[2], cfg):
            out.write(line)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
