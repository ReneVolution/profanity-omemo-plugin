from __future__ import unicode_literals

import os

here = os.path.abspath(__file__)
stanzas_root = os.path.join(os.path.dirname(here), 'stanzas')


def get_stanza_fixture(name):
    stanza_path = os.path.join(stanzas_root, name)

    with open(stanza_path, 'rb') as stanza_file:
        stanza = stanza_file.read()

    return stanza