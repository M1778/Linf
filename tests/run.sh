#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 -I "$HERE/run.py" --finc "${FINC:-finc}" \
    --fin-libs "${SDK_LIB:-${FIN_LIBS:-}}" --opt="${OPT:--O0}"
