#!/usr/bin/env python
# vim:ts=2:sw=2:et:

from __future__ import print_function
import os, sys, re, json
from os.path import dirname, basename, abspath
import subprocess
from subprocess import Popen, PIPE, STDOUT, check_output
from cStringIO import StringIO

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
  scratch = StringIO()
  cmd = ['config-get', 'og_content']
  scratch.write(check_output(cmd))
  scratch.seek(0) # must rewind before we read again
  og_content = json.load(scratch)

  for repo in og_content['repos']:
    url_proto = None
    url = None
    alias = None

    try:
      if repo['url'] is None:
        raise ValueError
    except ValueError:
      juju_log("Broken configuration file, url value is missing!")
      raise
    except KeyError:
      juju_log("Broken configuration file, url key is missing!")
      raise
    else:
      url = repo['url']

    try:
      if repo['alias'] is None:
        raise ValueError
    except ValueError:
      juju_log("Broken configuration file, alias value is missing!")
      raise
    except KeyError:
      juju_log("Broken configuration file, alias key is missing!")
      raise
    else:
      alias = repo['alias']

    if re.match("^(lp:|lp:\~|bzr:\/\/|bzr+ssh:\/\/)", url) != None:
      juju_log("matched a bzr url %{0}".format(url))
      url_proto='bzr'

    if re.match("(^git@|^git:\/\/|\.git$)", url) != None:
      juju_log("matched a git url %{0}".format(url))
      url_proto='git'

    cmd = [ 'config-get', 'grok_src' ]
    grok_src = check_output(cmd).strip()
    project = abspath(os.path.join(grok_src, alias))
    
    if os.path.exists(project):
      juju_log("Skipping project {0}, directory exists".format(project))
      continue

    try:
      {'git' : checkout_git,
       'bzr' : checkout_bzr} [url_proto](url, project)
    except KeyError:
      juju_log("repo protocol {0} currently unsupported".format(url_proto))
      raise

  update_index()

  return 0

if __name__ == "__main__":
  try:
    configure_opengrok()
  except Exception:
    sys.exit(1)

  sys.exit(0)
