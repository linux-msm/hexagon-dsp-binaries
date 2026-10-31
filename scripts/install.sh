#! /bin/sh
# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Linaro Ltd.
#
# Install DSP shell and libraries

set -e

if [ "$#" -ne 2 -o "$1" = "-h" -o "$1" = "--help" ]
then
	echo "Usage: $0 config.txt <destdir>" >&2
	exit 1
fi

CFG="$1"
DST="$2"

if ! [ -r "${CFG}" ]
then
	echo "config ${CFG} is unreadable" >&2
	exit 1
fi

mkdir -p "${DST}"

# dstdir srcdir
do_licence() {
	found=0
	while read line ; do
		[ "$line" = "Dir: $2" ] && break
	done
	while read line ; do
		lic=${line##Licence: }
		if [ "$lic" != "$line" ]
		then
			install -m 0644 $lic "$1" || exit 1
			found=1
			break
		fi
	done
	if [ $found -eq 0 ] ; then
		echo "License for $2 not found"
		exit 1
	fi
}

# dest subdir DSP QC_IMAGE_VERSION_STRING
# FIXME: maybe install only a fixed set of files
do_install() {
	local srcdir="$2/$4"
	local dstdir="$1/$2/dsp/$3"

	mkdir -p "${dstdir}"
	install -m 0644 "${srcdir}"/* "${dstdir}"

	do_licence "${dstdir}" "${srcdir}" < WHENCE
}

# dest board DSP source-board
do_reuse() {
	local target="$1/$4/dsp/$3"
	local link="$1/$2/dsp/$3"

	mkdir -p "`dirname "${link}"`"
	rm -f "${link}"
	ln -sr -T "${target}" "${link}"
}

# dest config
# Generate conf.d/*.yaml target configuration from Machine: and Arch: entries
do_conf() {
	mkdir -p "$1/conf.d"

	awk -v dst="$1/conf.d" '
	$1 == "Machine:" {
		name = $0
		sub(/^Machine:[ \t]+[^ \t]+[ \t]+/, "", name)
		if (!($2 in names))
			boards[count++] = $2
		names[$2] = names[$2] name "\n"
	}
	$1 == "Arch:" {
		archs[$2] = archs[$2] "    " toupper($3) "_ARCH: " $4 "\n"
	}
	END {
		for (i = 0; i < count; i++) {
			board = boards[i]
			file = board
			sub(/^[^\/]*\//, "", file)
			gsub(/\//, "-", file)
			file = dst "/hexagon-dsp-binaries-" tolower(file) ".yaml"

			printf "# SPDX-License-Identifier: MIT\n" > file
			printf "# Generated from config.txt\n" > file
			printf "# yaml-language-server: $schema=schema.json\n" > file
			printf "machines:\n" > file
			n = split(names[board], list, "\n")
			for (j = 1; j < n; j++)
				printf "  \"%s\":\n    DSP_LIBRARY_PATH: %s/dsp\n%s", \
					list[j], board, archs[board] > file
			close(file)
		}
	}' "$2"
}

grep -v '^#\|^$' "${CFG}" | while read verb rest
do
	case ${verb} in
	"Install:" )
		do_install ${DST} ${rest}
		;;
	"Reuse:" )
		do_reuse ${DST} ${rest}
		;;
	"Machine:" | "Arch:" )
		# handled by do_conf
		;;
	* )
		echo "Unsupported clause ${verb}" >&2
		exit 1
	esac
done

do_conf "${DST}" "${CFG}"
