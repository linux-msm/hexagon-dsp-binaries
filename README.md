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

# Maintainer workflow

## Adding new binaries

1. Place the new binary directory under the appropriate SoC path (e.g.
   `qcs6490/Thundercomm/RubikPi3/<version>/`).
2. Add a `Dir:` line for the new directory to `WHENCE`. Each `WHENCE` block
   lists one or more `Dir:` lines, sorted alphabetically, followed by the
   `Device:`, `Licence:`, `Status:` and optional `Origin:` fields shared by
   all of them. If the device already has a block with the same `Device:`,
   `Licence:` and `Status:` fields and no `Origin:`, add the new `Dir:` line
   to that block, keeping the lines sorted. Otherwise (e.g. when the binaries
   come with a different licence or a specific `Origin:` URL), add a new
   block. Blocks are sorted alphabetically by their first `Dir:` line, so
   place a new block accordingly.
3. Add an `Install:` line to `config.txt` referencing the new path. Each
   `config.txt` section, headed by a comment, describes one board: the
   `Install: <board> <DSP> <release>` lines for its DSPs and the
   `Reuse: <board> <DSP> <source board>` lines for the DSPs using binaries
   installed for another board. The older
   `Link: <source board>/dsp/<DSP> <board>/dsp/<DSP>` lines are equivalent
   to `Reuse:` ones. Sections are sorted by the board path (the destination
   of `Link:` lines), and lines within a section are sorted by DSP. The DSP
   of the source board of every `Reuse:` and `Link:` line must be installed
   by an `Install:` line.
4. Run `make check` to validate the new entries.

## Validating against an installed linux-firmware tree

To verify that the version strings declared in `config.txt` match those
embedded in the actual binaries:

    ./scripts/checkfw.py <path-to-linux-firmware>

## Cutting a release

    ./scripts/release.sh <tag>

This will run `make check`, create a signed git tag, produce a tarball under
`dist/`, and sign it with GPG.
