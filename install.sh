#!/usr/bin/env bash
set -e

python setup.py install --force --user --prefix=
mkdir -p ~/.local/share/profanity/plugins
cp deploy/prof_omemo_plugin.py ~/.local/share/profanity/plugins/
