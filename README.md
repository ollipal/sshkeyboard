# sshkeyboard

The only keyboard that works in _all_ unix environments

No dependencies

Works without sudo and without x server

But... it has some drawbacks due to the limitations

My own usecase is to use this when I want to have some keyboard
callback through ssh on machines
without x server or when I'm using

-- relation to pynput and keyboard

-- graph

## How it works

It captures, and parses the terminal input in real time,
and fires callbacks based on the user input

Supports normal syncronous, concurrent and asyncrynous modes!

## why does not support windows

Requires [fcntl](https://docs.python.org/3/library/fcntl.html) module.

Anyways in my experience other libraries know how to handle Windows