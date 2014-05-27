#!/usr/bin/env python

import argparse
import os, re, cStringIO

parser = argparse.ArgumentParser(description="Tool for updating haproxy.cfg")
parser.add_argument('command', choices=['reset', 'update'])
args = parser.parse_args()

config_file_path = os.path.join('etc', 'haproxy', 'haproxy.cfg')

class Block(object):
  def __init__(self):
    self.lines = []
  def append(self, line):
    self.lines.append(line)
  def __str__(self):
    return ''.join(self.lines)

class UnknownBlock(Block):
  pass

class GlobalBlock(Block):
  pass

class DefaultsBlock(Block):
  pass

class FrontendBlock(Block):
  pass

class BackendBlock(Block):
  pass

class ListenBlock(Block):
  pass

block_map = [
  (re.compile('^\s*global\s+'  ), GlobalBlock   ),
  (re.compile('^\s*defaults\s+'), DefaultsBlock ),
  (re.compile('^\s*frontend\s+'), FrontendBlock ),
  (re.compile('^\s*backend\s+' ), BackendBlock  ),
  (re.compile('^\s*listen\s+'  ), ListenBlock   )
]

def parse_haproxy_config():
  config = []
  with open(config_file_path, 'r') as in_file:
    current_block=UnknownBlock()
    for line in in_file.readlines(): 
      for (regex, NewBlock) in block_map:
        if regex.match(line):
          config.append(current_block)
          current_block = NewBlock()
          break
      current_block.append(line)
    config.append(current_block)
  return config

def remove_routing_blocks():
  config = parse_haproxy_config() 
  with open(config_file_path, 'w') as config_file:
    for block in config:
      if type(block) is DefaultsBlock:
        config_file.write(block.__str__())
      elif type(block) is GlobalBlock:
        config_file.write(block.__str__())
      elif type(block) is UnknownBlock:
        config_file.write(block.__str__())

import etcd

class Node(object):
  def __init__(self, createdIndex, modifiedIndex, key, nodes=None, value=None, expiration=None, ttl=None, dir=False):
    self.createdIndex = createdIndex
    self.modifiedIndex = modifiedIndex
    self.key = key
    self.value = value
    self.expiration = expiration
    self.ttl = ttl
    self.dir = dir
    self.nodes = map(lambda n: Node(**n), nodes) if nodes != None else []
    self.short_key = key.split('/')[-1]

def getBackendsFromEtcd():
  (host, port) = os.environ.get('ETCD_PEERS', ':').split(':')
  if (not host and not port):
    client = etcd.Client()
  elif ( host and port ):
    client = etcd.Client(host=host, port=port)
  else:
    raise ValueError("Bad parameters for etcd connection")
  backends = {}
  for backend in (Node(**n) for n in client.read('/mayfly/backends', recursive=True)._children):
    for version in backend.nodes:
      for host in version.nodes:
        backends.setdefault("%s_%s" % (backend.short_key, version.short_key), []).append(host.value) 
  return backends

from jinja2 import Environment, FileSystemLoader

def updateBackendsFromEtcd():
  backends = getBackendsFromEtcd()
  env = Environment(loader=FileSystemLoader(os.environ.get('MAYFLY_TEMPLATES', '/etc/mayfly/templates')))
  output_filename = os.environ.get('MAYFLY_HAPROXY_CFG', '/etc/haproxy/haproxy.cfg')
  template = env.get_template('haproxy.cfg.jinja')
  with open(output_filename, 'w') as output_file:
    output_file.write(template.render(backends=backends, enumerate=enumerate))

if __name__ == '__main__':

  if args.command == 'reset':
    remove_routing_blocks()
  elif args.command == 'update':
    updateBackendsFromEtcd()
