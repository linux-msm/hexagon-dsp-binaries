# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2025 Linaro Ltd.

prefix ?= /usr
DSPDIR = ${prefix}/share/qcom

all:

clean:

install:
	./scripts/install.sh config.txt ${DESTDIR}/${DSPDIR}
	install -d -m 0755 ${DESTDIR}/${DSPDIR}/conf.d/
	install -m 0644 conf.d/*.yaml ${DESTDIR}/${DSPDIR}/conf.d/
	install -m 0644 conf.d/schema.json ${DESTDIR}/${DSPDIR}/conf.d/

TAG = $(shell git describe)
NAME = hexagon-dsp-binaries
TARGET = $(NAME)_$(TAG).tar.gz
SUBDIR = $(NAME)-$(TAG)
dist:
	$-rm -rf release
	@mkdir -p release dist
	./scripts/dist.sh config.txt release/$(SUBDIR)
	tar -czf release/$(TARGET) -C release $(SUBDIR)
	$(MAKE) -C release/$(SUBDIR) check
	$(MAKE) -C release/$(SUBDIR) install DESTDIR=$(CURDIR)/release/test-install-$(TAG)
	mv release/$(TARGET) dist/$(TARGET)
	@echo "Created dist/$(TARGET)"
	@rm -rf release

check:
	./scripts/check.py
ifdef FIRMWARE
	./scripts/checkfw.py $(FIRMWARE)
endif

.PHONY: dist check
