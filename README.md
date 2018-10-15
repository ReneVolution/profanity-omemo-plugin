
[![Project Status](https://img.shields.io/badge/Project%20Status-Unmaintained-red.svg)](https://github.com/ReneVolution/profanity-omemo-plugin)


# profanity-omemo-plugin  [![OMEMO Logo](./docs/images/omemo.png)](https://conversations.im/omemo/)

A Python plugin to use (axolotl / Signal Protocol) encryption for the [Profanity](http://www.profanity.im/) XMPP messenger

## Requirements

This Plugin requires the ProfanityIM Messenger to be compiled with Python [2.7, 3.5, 3.6] Plugin Support. 
Please make sure to match the Plugin-Host requirements from the table below.

| Plugin  | Profanity |
|-------------|----------------|
| master | master |
| v0.1.1 | \>= v0.5.0 |
| v0.1.0 | \>= v0.5.0 |


## Prerequisites

__Linux__

Some Linux distributions require to install some header packages before installing the PyPI cryptography package. 
Please find more details at [cryptography.io](https://cryptography.io/en/latest/installation/#building-cryptography-on-linux).

__Android (Termux)__

- Run `apt install git clang libffi-dev openssl-dev`
- Run `export CONFIG_SHELL="$PREFIX/bin/sh"`

<br/>
**You will also need `setuptools` (e.g. through `pip install setuptools`).**


## Installation

- Clone this Repository
- Run `./install.sh`
- Open `profanity`
- Load plugin with `/plugins load prof_omemo_plugin.py`

## Usage

`/omemo (on|off)` </br>
Turns on/off the usage of the plugin while it may be still loaded in profanity. (Default=ON)

`/omemo status` </br>
Displays the current status in profanity's console window

`/omemo start [contact jid]` </br>
Starts a new conversation with the given contact, if not given, the one in the current chat

`/omemo end [contact jid]` </br>
Ends the conversation with the given contact jid or, if not given, the one in the current chat 

## Contributing

If you want to contribute to this project, please check out [CONTRIBUTING.md](./CONTRIBUTING.md) first.

## TODO

- [ ] Documentation
- [ ] Handle messages from own devices
- [ ] Trust Management
- [ ] Write more tests

