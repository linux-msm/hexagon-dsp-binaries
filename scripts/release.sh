#!/bin/sh
# SPDX-License-Identifier: MIT
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
#
# Tag, package, and sign a new release tarball

set -e
make check
git tag -s -m "Hexagon DSP binaries, release $1" $1
make dist
gpg --sign -b -a dist/hexagon-dsp-binaries_$1.tar.gz
