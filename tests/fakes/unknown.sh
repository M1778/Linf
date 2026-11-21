#!/bin/sh
# =============================================================================
# Fin Programming Language
#
# Made with ❤️ for someone special.
#
# This project is genuinely built on love and dedication, a way to express your love can be done through Fin.
# Fin is a semi-object-orientated programming language that specialized in control, giving so much control to the user while asking for the bare minimum.
# Fin is the name of the Angel from BlackNightmare-Stories not yet published.
# “Love is the reason this project exists”
# -----------------------------------------------------------------------------
# Author: M1778
# Repository: https://github.com/M1778/linf
# Profile: https://github.com/M1778M/
# -----------------------------------------------------------------------------
# Copyright (C) 2027 M1778
#
# This file is part of linf, a project for the Fin Programming Language.
#
# Licensed under the MIT License. See LICENSE in the repository root.
#
# SPDX-License-Identifier: MIT
# =============================================================================

# A fake finc for the self-check: an UNKNOWN kind plus one known diagnostic.
# The contract lane carries the unknown kind on untouched; the built lanes
# skip it (a rendered line cannot represent it) and keep the diagnostic.
echo '{"kind":"weather","message":"unknown kind line","file":"f1.fin","line":1,"column":1}' >&2
echo '{"kind":"diagnostic","severity":"error","code":null,"message":"known diagnostic","file":"f2.fin","line":4,"column":2,"endLine":4,"endColumn":3,"help":null,"attribution":null}' >&2
echo '{"kind":"summary","errors":1,"warnings":0,"exitCode":1,"status":"failed"}' >&2
exit 1
