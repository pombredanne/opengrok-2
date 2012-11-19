#!/usr/bin/env python
# vim:ts=2:sw=2:et:

from __future__ import print_function
import os, sys, logging, re, json
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
    juju_log(buf, level=self.levelmap())
    for line in buf.rstrip().splitlines():
      self.logger.log(self.log_level, line.rstrip())

def juju_log(args, level='INFO'):
  Popen(['juju-log', '-l', level, args])

def error(args):
  print(args, file=sys.stderr)

def checkout_git(url, path):
  args = "git clone {0} {1}".format(url, path)
  Popen(args.split(' '))

def checkout_bzr(url, path):
  args = "bzr branch {0} {1}".format(url, path)
  Popen(args.split(' '))

def update_index():
  print("updating index now")
  Popen("initctl start --no-wait opengrok-index".split(' '))

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
      error("Broken configuration file, url value is missing!")
      raise
    except KeyError:
      error("Broken configuration file, url key is missing!")
      raise
    else:
      url = repo['url']

    try:
      if repo['alias'] is None:
        raise ValueError
    except ValueError:
      error("Broken configuration file, alias value is missing!")
      raise
    except KeyError:
      error("Broken configuration file, alias key is missing!")
      raise
    else:
      alias = repo['alias']

    if re.match("^(lp:|lp:\~|bzr:\/\/|bzr+ssh:\/\/)", url) != None:
      print("matched a bzr url {0}".format(url))
      url_proto='bzr'

    if re.match("(^git@|^git:\/\/|\.git$)", url) != None:
      print("matched a git url {0}".format(url))
      url_proto='git'

    cmd = [ 'config-get', 'grok_src' ]
    grok_src = check_output(cmd).strip()
    project = abspath(os.path.join(grok_src, alias))
    
    if os.path.exists(project):
      print("Skipping project {0}, directory exists".format(project))
      continue

    try:
      {'git' : checkout_git,
       'bzr' : checkout_bzr} [url_proto](url, project)
    except KeyError:
      error("repo protocol {0} currently unsupported".format(url_proto))
      raise

  update_index()

  return 0

if __name__ == "__main__":
  try:
    logging.basicConfig(
       level=logging.DEBUG,
       format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
       filename=os.path.join('/var/log/juju', 'opengrok-common.log'),
       filemode='a'
    )

    # STDOUT and STDERR simultaniously go to logfile and juju-log
    # Popen is called without shell so atleast output goes to auxilary logfile
    sys.stdout = StreamToLogger(logging.getLogger('STDOUT'),
                                logging.INFO)
    sys.stderr= StreamToLogger(logging.getLogger('STDERR'),
                                logging.ERROR)
    configure_opengrok()
  except Exception as e:
    print("unhandled exception caught in main: {0}".format(type(e)))
    print("XXX {0}:{1}".format(e.args,e.message))
    sys.exit(1)

  sys.exit(0)
