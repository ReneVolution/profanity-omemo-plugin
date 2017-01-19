
[![Project Status](https://img.shields.io/badge/Project%20Status-Early%20Beta-red.svg)](https://github.com/ReneVolution/profanity-omemo-plugin)
[![Build Status](https://travis-ci.org/ReneVolution/profanity-omemo-plugin.svg?branch=master)](https://travis-ci.org/ReneVolution/profanity-omemo-plugin)
[![Coverage Status](https://coveralls.io/repos/github/ReneVolution/profanity-omemo-plugin/badge.svg?branch=master)](https://coveralls.io/github/ReneVolution/profanity-omemo-plugin?branch=master)
[![Say Thanks](https://img.shields.io/badge/SayThanks.io-%E2%98%BC-1EAEDB.svg)](https://saythanks.io/to/ReneVolution)



# profanity-omemo-plugin  [![OMEMO Logo](./docs/images/omemo.png)](https://conversations.im/omemo/)

A Python plugin to use (axolotl / Signal Protocol) encryption for the profanity XMPP messenger


## Installation

The easiest way to install the plugin is to use the provided `install.sh` script in this repository.
After installing you have to enable the plugin inside profanity with `/plugins load prof_omemo_plugin.py`.

## Usage

`/omemo status` => Displays the current status in profanity's console window
`/omemo start [contact jid]` => Starts a new conversation with the given contact, if not given, the one in the current chat
`/omemo end [contact jid]` => Ends the conversation with the given contact jid or, if not given, the one in the current chat 

## TODO

- [ ] Documentation
- [ ] Handle messages from own devices
- [ ] Trust Management
- [ ] Write more tests

