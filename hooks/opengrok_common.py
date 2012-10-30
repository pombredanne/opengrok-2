#!/usr/bin/env python3
# -*- coding: utf=8 -*-
# vim:ts=2:sw=2:et:

import os, sys
from os.path import dirname, basename, abspath
from subprocess import Popen

# XXX must import variables set in inc/common, export grok settings
CHARM_ROOT = os.environ['PWD']
COMMAND = basename(abspath(__file__))

def juju_log(args):
    Popen(['juju-log', args], shell=False)

def configure_opengrok():
    og_content = Popen("config-get og-content", shell=True).strip()

    if og_content.startswith('lp:'):
        repo_name = og.content.split(':')[-1]
    else:
        juju_log("No lp branch provided, failing safe")
        return 0

    # Handle slashified urls
    (head, tail) = os.path.split(repo_name)

    # We define some naming policy here, to safe guard against paths
    # like lp:foo/bar/project/trunk, we take name like this and make
    # a new project name of project_trunk. Yes I know this leaves things
    # out like release but it's either this or a runtime config alias
    # that I can't always count on people providing. We may eventually
    # get there but in the meanwhile lets do something sensible.
    if head is not None and tail is not None:
        (new_head, new_tail) = os.path.split(head)
        repo_name = new_head + '_' + tail
    else:
        repo_name = tail

    repo_path = os.path.join(grok_src, repo_name)

    if os.path.exists(repo_path):
        juju_log("Updating existing branch - {0}".format(og_content))
    else
        juju_log("Checking out new branch - {0}".format(og_content))
        result = Popen("bzr branch {0} {1}".format(og_content, repo_path),
                shell=True)
        # XXX check return value, DO NOT FAIL if non zero.
        # TODO now what?
    
    # update config and update index
    Popen("initctl emit --no-wait opengrok-index", shell=True)
    return 0

# There's no switch/case in python but this construct is just as good
try:
    {'config-changed': configure_opengrok}[COMMAND]()
except KeyError:
    juju_log("Command not supported")

sys.exit(0)
