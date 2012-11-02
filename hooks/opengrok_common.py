#!/usr/bin/env python
# vim:ts=2:sw=2:et:

from __future__ import print_function
import os, sys, json
from os.path import dirname, basename, abspath
from subprocess import Popen, PIPE
from tempfile import TemporaryFile as mkstemp

COMMAND = basename(abspath(__file__))

def juju_log(args):
    Popen(['juju-log', args], shell=False)

def configure_opengrok():
    print ('entering config-changed')

    scratch = mkstemp(mode='rw+b')
    task = Popen("config-get og-content", stdout=scratch, shell=True)
    task.communicate()

    # must rewind before we read again 
    scratch.seek(0) 
    og_content = json.load(scratch)
    scratch.close()

    for repo in og_content['repos']:
      out = "1:{0} 2:{1}".format(repo['url'], repo['alias'])
      juju_log(out)
      print (out)

    return 0
    # update config and update index
#    Popen("initctl emit --no-wait opengrok-index", shell=True)
#    return 0

# There's no switch/case in python but this construct is just as good
try:
    {'config-changed': configure_opengrok}[COMMAND]()
except KeyError:
    juju_log("Command not supported")

sys.exit(0)
