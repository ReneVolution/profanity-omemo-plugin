#!/usr/bin/env bash
set -e

which profanity > /dev/null
which scanelf > /dev/null
which tail > /dev/null
which cut > /dev/null
which tr > /dev/null
which sed > /dev/null

profanity="$(which profanity)"
python_version="$(scanelf -n "${profanity}" | tail -n+2 | cut -d' ' -f2 | tr , '\n' | sed -nre 's/^libpython([0-9]+\.[0-9]+).*$/\1/p')"

python"${python_version}" setup.py install --force --user --prefix=
mkdir -p ~/.local/share/profanity/plugins
cp deploy/prof_omemo_plugin.py ~/.local/share/profanity/plugins/
