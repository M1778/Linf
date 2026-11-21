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

# A fake finc for the self-check: a warning and a clean summary. A finc
# warning is not a linf finding and finc itself is happy, so EVERY lane
# must exit 0 -- the lanes used to disagree here.
echo '{"kind":"diagnostic","severity":"warning","code":null,"message":"just a warning","file":"f1.fin","line":2,"column":1,"endLine":2,"endColumn":2,"help":null,"attribution":null}' >&2
echo '{"kind":"summary","errors":0,"warnings":1,"exitCode":0,"status":"ok"}' >&2
exit 0
