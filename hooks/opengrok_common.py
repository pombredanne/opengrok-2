#!/usr/bin/env python
# vim:ts=2:sw=2:et:

from __future__ import print_function
import os, sys, re, json
from os.path import dirname, basename, abspath
import subprocess
from subprocess import Popen, PIPE
from tempfile import TemporaryFile as mkstemp

COMMAND = basename(abspath(__file__))

def juju_log(args):
  Popen(['juju-log', args], shell=False)

def checkout_git(url, path):
  Popen("git clone {0} {1}".format(url, path), shell=True).communicate()

def checkout_bzr(url, path):
  Popen("bzr branch {0} {1}".format(url, path), shell=True).communicate()

def update_index():
  Popen("initctl start opengrok-index", shell=True).communicate()

def configure_opengrok():
  scratch = mkstemp(mode='rw+b')
  task = Popen("config-get og_content", stdout=scratch,
      shell=True).communicate()

  scratch.seek(0) # must rewind before we read again
  og_content = json.load(scratch)

  for repo in og_content['repos']:
    url_proto=None

    juju_log("XXX {0} -- {1}".format(repo['url'], repo['alias']))
    # XXX can't just silently ignore stuff
    if repo['url'] is None:
      continue

    if repo['alias'] is None:
      # XXX slashifying is just too much work, provide an alias or FAIL
      # XXX create exception and exit(1)
      continue

    if re.match("^(lp:|lp:\~|bzr:\/\/|bzr+ssh:\/\/)", repo['url']) != None:
      juju_log("matched a bzr url %{0}".format(repo['url']))
      url_proto='bzr'

    if re.match("(^git@|^git:\/\/|\.git$)", repo['url']) != None:
      juju_log("matched a git url %{0}".format(repo['url']))
      url_proto='git'

    try:
      cmd = [ 'config-get', 'grok_src' ]
      grok_src = subprocess.check_output(cmd).strip()
      project = abspath(os.path.join(grok_src, repo['alias']))
      
      if os.path.exists(project):
        # consider always overwrite flag
        juju_log("Skipping project {0}, directory exists".format(project))
        continue

      try:
        {'git' : checkout_git,
         'bzr' : checkout_bzr} [url_proto](repo['url'], project)
      except KeyError:
        juju_log("repo protocol {0} currently unsupported".format(url_proto))

    except KeyError:
      juju_log("env key not found, was inc/common loaded?")

  update_index()

  return 0
try:
  {'py-config-changed': configure_opengrok}[COMMAND]()
except KeyError:
  juju_log("Command not supported")

sys.exit(0)
