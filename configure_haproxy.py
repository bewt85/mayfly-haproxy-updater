#!/usr/bin/env python

import argparse
import os, re, cStringIO

parser = argparse.ArgumentParser(description="Tool for updating haproxy.cfg")
parser.add_argument('command', choices=['reset'])
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

if __name__ == '__main__':

  if args.command == 'reset':
    remove_routing_blocks()
