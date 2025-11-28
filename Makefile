# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2025 Linaro Ltd.

prefix ?= /usr
DSPDIR = ${prefix}/share/qcom

all:

clean:

install:
	./scripts/install.sh config.txt ${DESTDIR}/${DSPDIR}
	install -D -m 0644 00-hexagon-dsp-binaries.yaml ${DESTDIR}/${DSPDIR}/conf.d/00-hexagon-dsp-binaries.yaml

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
