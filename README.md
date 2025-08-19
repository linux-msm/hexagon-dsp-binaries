# Qualcomm DSP binaries

While linux-firmware contains firmware for the DSPs present on the devices
using Qualcomm SoCs, using the FastRPC interfaces, compressed audio support or
getting the sensors data on those devices requires additional set of binaries
to be executed on the DSP side.

These binaries include `fastrpc_shell_N` (where N is 0, 1, 2, 3),
`fastrpc_shell_unsigned_N` (N = 3, special version of shell for CDSP only),
libraries implementing necessary hooks, etc.

This repo provides a central repository for handling these files.

# Design decisions

These binary files are tied to the particular SoC and DSP firmware revision. As
such it is impossible to provide a single set of binaries that works for all
the targets. Moreover, different versions of linux-firmware require
corresponding set of binaries.

For this reason this repo includes all binaries at the same time. The exact set
to be installed is selected via the `config.txt` file present in the repo. This
provides flexibility to users, while still allowing trunk revision to track the
top of the tree of the linux-firmware repo.

# Data origin

WHENCE file documents orignal locations for the tarballs with the library files.
