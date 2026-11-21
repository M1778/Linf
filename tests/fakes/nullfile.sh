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

# A fake finc for the self-check: a diagnostic with a null file, the shape
# finc writes for a path it could not read. The built lanes must render it
# location-less -- never under a filename borrowed from the next key.
echo '{"kind":"diagnostic","severity":"error","code":null,"message":"could not read file: x.fin","file":null,"line":0,"column":0,"endLine":0,"endColumn":0,"help":null,"attribution":null}' >&2
echo '{"kind":"summary","errors":1,"warnings":0,"exitCode":2,"status":"failed"}' >&2
exit 2
