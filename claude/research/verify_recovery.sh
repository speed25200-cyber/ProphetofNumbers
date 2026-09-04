#!/usr/bin/env sh
set -eu

cc=${CC:-cc}

"$cc" -O3 -std=c11 -Wall -Wextra -Werror -o mtbreak mtbreak.c
"$cc" -O3 -std=c11 -Wall -Wextra -Werror -o keno_break keno_break.c
python3 -m unittest discover -v

./keno_break demo 400 0xC0FFEE42 41 0 0 20
./keno_break demo 400 0xC0FFEE42 41 0 0 21

set +e
./keno_break demo 400 0xC0FFEE42 41 0 1 20
status=$?
set -e
if [ "$status" -ne 4 ]; then
    echo "expected the 400-draw modulo model to be INCONCLUSIVE (exit 4), got $status" >&2
    exit 1
fi

echo "state-recovery verification passed"
