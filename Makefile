# SPDX-License-Identifier: MIT

prefix ?= /usr
DSPDIR = ${prefix}/share/qcom

all:

clean:

install:
	./scripts/install.sh config.txt ${DESTDIR}/${DSPDIR}

TAG = $(shell git describe)
NAME = hexagon-dsp-binaries
TARGET = $(NAME)_$(TAG).tar.gz
SUBDIR = $(NAME)-$(TAG)
dist:
	$-rm -rf release
	@mkdir -p release dist
	./scripts/dist.sh config.txt release/$(SUBDIR)
	tar -czf dist/$(TARGET) -C release $(SUBDIR)
	@echo "Created dist/$(TARGET)"
	@rm -rf release

check:
	./scripts/check.py

.PHONY: dist check
