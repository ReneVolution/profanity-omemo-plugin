
[![Project Status](https://img.shields.io/badge/Project%20Status-Early%20Beta-red.svg)](https://github.com/ReneVolution/profanity-omemo-plugin)
[![Build Status](https://travis-ci.org/ReneVolution/profanity-omemo-plugin.svg?branch=master)](https://travis-ci.org/ReneVolution/profanity-omemo-plugin)
[![Coverage Status](https://coveralls.io/repos/github/ReneVolution/profanity-omemo-plugin/badge.svg?branch=master)](https://coveralls.io/github/ReneVolution/profanity-omemo-plugin?branch=master)
[![Say Thanks](https://img.shields.io/badge/SayThanks.io-%E2%98%BC-1EAEDB.svg)](https://saythanks.io/to/ReneVolution)
[![Bountysource](https://api.bountysource.com/badge/issue?issue_id=27781988)](https://www.bountysource.com/issues/27781988-omemo-support?utm_source=27781988&utm_medium=shield&utm_campaign=ISSUE_BADGE)



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

You will also need `setuptools` (e.g. through `pip install setuptools`).


## Installation

The easiest way to install the plugin is to use the provided `install.sh` script in this repository.
After installing you have to enable the plugin inside profanity with `/plugins load prof_omemo_plugin.py`.

## Usage

`/omemo (on|off)` </br>
Turns on/off the usage of the plugin while it may be still loaded in profanity. (Default=ON)

`/omemo status` </br>
Displays the current status in profanity's console window

`/omemo start [contact jid]` </br>
Starts a new conversation with the given contact, if not given, the one in the current chat

`/omemo end [contact jid]` </br>
Ends the conversation with the given contact jid or, if not given, the one in the current chat 

## TODO

- [ ] Documentation
- [ ] Handle messages from own devices
- [ ] Trust Management
- [ ] Write more tests

