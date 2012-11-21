#!/usr/bin/env python
# vim:ts=2:sw=2:et:

from __future__ import print_function
import os, sys, logging, re, shlex, json
from os.path import dirname, basename, abspath
from subprocess import Popen, PIPE, STDOUT, check_output
from cStringIO import StringIO

class StreamToLogger(object):
  """
  Fake file-list stream object that redirects writes to a logger
  instance and juju logging
  """
  def __init__(self, logger, log_level=logging.INFO):
    self.logger = logger
    self.log_level = log_level
    self.linebuf = ''

  def levelmap(self):
    try:
      return {logging.DEBUG:    'DEBUG',
              logging.INFO:     'INFO',
              logging.WARN:     'WARN',
              logging.ERROR:    'ERROR',
              logging.CRITICAL: 'CRITICAL'}[self.log_level]
    except KeyError:
      return 'INFO'

  def write(self, buf):
    for line in buf.rstrip().splitlines():
      self.logger.log(self.log_level, line.rstrip())
      juju_log(self.levelmap(), line.rstrip())

def juju_log(level, args):
  p = Popen(['juju-log', '-l', level, args])
  p.wait()

def error(args):
  print(args, file=sys.stderr)

def checkout_git(url, path):
  print("Checking out git branch {0} to path {1}".format(url, path))
  args = "git clone {0} {1}".format(url, path)
  p = Popen(shlex.split(args))
  return p

def checkout_bzr(url, path):
  print("Checking out bzr branch {0} to path {1}".format(url, path))
  args = "bzr branch {0} {1}".format(url, path)
  p = Popen(shlex.split(args))
  return p

def update_index_sync():
  from time import sleep
  print("Preparing to update configuration and index synchronously")

  cmd = "initctl status opengrok-index"
  updated = False

  for i in range(0,5):
    if updated: break

    out = check_output(shlex.split(cmd)).strip()
    state = re.search('(\w+)\/(\w+)', out)

    if state is None:
      error("Unable to determine opengrok-index state")
      sleep(10)
      continue

    state = state.groups()

    if state[0] != 'stop' or state[1] != 'waiting':
      print("{0}: opengrok indexer is busy, wait and retry a bit".format(i))
      sleep(60)
    else:
      print("Project configuration and index update...")
      p = Popen(['initctl', 'start', 'opengrok-index'])
      p.wait()
      updated = True
      print("Project configuration and index update complete")

  if not updated:
    print("We waited five minutes for previous index to finish \n" 
        "to no avail. Failing safe and *not* updating configuration file \n"
        "and beginning new index operation. Wait until opengrok-index job \n"
        "has stopped and 'initctl start opengrok-index' manually \n")

def configure_opengrok():
  print("Entering py-config-changed")

  cmd = ['config-get', 'og_content']
  scratch = StringIO()
  scratch.write(check_output(cmd))
  scratch.seek(0) # must rewind before we read again
  og_content = json.load(scratch)

  try:
    if og_content is None:
      raise ValueError("Failed to parse og_content JSON")
    og_content['repos']
  except:
    error("Something is wrong with the parsed json, can't reference root array 'repos'")
    raise

  cmd = [ 'config-get', 'grok_src' ]
  grok_src = check_output(cmd).strip()

  if grok_src is None:
    raise ValueError("Failed to retrieve grok_src from zookeeper for some reason")

  checkouts = [] # array of processes for sync point

  for repo in og_content['repos']:
    url_proto = None
    url = None
    alias = None

    try:
      for key in ('url', 'alias'):
        if repo[key] is None:
          raise ValueError("Value for {0} is missing, fatal error".format(key))
    except ValueError as e:
      error(e.message)
      raise
    except KeyError as e:
      error("Broken configuration file, {0} key is missing!".format(e.message))
      raise
    else:
      url   = repo['url']
      alias = repo['alias']

    if re.search("^(lp:|lp:\~|bzr:\/\/|bzr+ssh:\/\/)", url) != None:
      print("matched a bzr url {0}".format(url))
      url_proto='bzr'

    if re.search("(^git@|^git:\/\/|\.git$)", url) != None:
      print("matched a git url {0}".format(url))
      url_proto='git'

    project = abspath(os.path.join(grok_src, alias))
    
    if os.path.exists(project):
      print("Skipping project {0}, directory exists".format(project))
      continue

    try:
      run = {'git' : checkout_git,
             'bzr' : checkout_bzr} [url_proto]
      checkouts.append(run(url, project))
    except KeyError:
      error("Repo protocol {0} currently unsupported".format(url))
      raise

  # sync point, ensure all branches have finished cloning
  # before updating project config and building index
  print("Waiting for all branch checkouts to finish...")
  for p in checkouts:
    p.wait()
  print("Branch checkouts complete")

  update_index_sync()

  print("Exiting py-config-changed")
  return 0

if __name__ == "__main__":
  try:
    logging.basicConfig(
       level=logging.DEBUG,
       format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
       filename=os.path.join('/var/log/juju', 'opengrok-common.log'),
       filemode='a'
    )

    # STDOUT and STDERR simultaneously go to logfile and juju-log
    # Popen is called without shell so at least output goes to auxiliary logfile
    sys.stdout = StreamToLogger(logging.getLogger('STDOUT'),
                                logging.INFO)
    sys.stderr= StreamToLogger(logging.getLogger('STDERR'),
                                logging.ERROR)
    configure_opengrok()
  except Exception as e:
    error("Unhandled exception caught in main: {0}".format(type(e)))
    error("XXX {0}:{1}".format(e.args,e.message))
    sys.exit(1)

  sys.exit(0)
