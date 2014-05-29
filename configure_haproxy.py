#!/usr/bin/env python

import argparse
import os, re, cStringIO

parser = argparse.ArgumentParser(description="Tool for updating haproxy.cfg")
parser.add_argument('command', choices=['update'])
args = parser.parse_args()

import etcd

def getEtcdClient():
  (host, port) = os.environ.get('ETCD_PEERS', ':').split(':')
  if (not host and not port):
    client = etcd.Client()
  elif ( host and port ):
    client = etcd.Client(host=host, port=int(port))
  else:
    raise ValueError("Bad parameters for etcd connection")
  return client

def getEtcdNode(key):
  client = getEtcdClient()
  return Node(**client.read(key).__dict__)

class Node(object):
  def __init__(self, createdIndex, modifiedIndex, key, nodes=None, value=None, expiration=None, ttl=None, dir=False, **kwargs):
    self.createdIndex = createdIndex
    self.modifiedIndex = modifiedIndex
    self.key = key
    self.value = value
    self.expiration = expiration
    self.ttl = ttl
    self.dir = dir
    self.nodes = map(lambda n: Node(**n), nodes) if nodes != None else []
    self.short_key = key.split('/')[-1]
  def ls(self):
    if self.dir and not self.nodes:
      client = getEtcdClient()
      self.nodes = [Node(**n) for n in client.read(self.key, recursive=True)._children]
    return self.nodes
  def __repr__(self):
    if self.value:
      return "%s => %s" % (self.key, self.value)
    else:
      return "\n".join(node.__repr__() for node in self.ls())

def getBackendsFromEtcd():
  client = getEtcdClient()
  backends = {}
  for backend in (Node(**n) for n in client.read('/mayfly/backends', recursive=True)._children):
    for version in backend.nodes:
      for host in version.nodes:
        backends.setdefault("%s_%s" % (backend.short_key, version.short_key), []).append(host.value) 
  return backends

def getFrontendsFromEtcd():
  client = getEtcdClient()
  # /mayfly/environments/<name>/prefix                       => www
  # /mayfly/environments/<name>/header                       => prod
  # /mayfly/environments/<name>/services/<service>/<version> => 0
  frontends = {}
  for frontend in (Node(**n) for n in client.read('/mayfly/environments', recursive=True)._children):
    (env_name, prefix, header) = (frontend.short_key, None, None)
    for node in frontend.nodes:
      if node.short_key == 'prefix':
        prefix == node.value
        frontends.setdefault('prefixes', []).append(prefix)
      elif node.short_key == 'header':
        header == node.value
      elif node.short_key == 'service':
        for service in node.nodes:
          service_name = service.short_key
          frontend.setdefault('services', []).append(service_name)
          version = service.nodes[0].short_key
          if len(service.nodes) > 1:
            raise ValueError("Etcd returns more than one version of %s in the $s environment.  Aborting" % (service_name, env_name))
          frontends.setdefault('backends', []).append((env_name, version, service_name))
    frontends.setdefault('environments', []).append((env_name, prefix, header))
  return frontends

from jinja2 import Environment, FileSystemLoader

def updateBackendsFromEtcd():
  backends = getBackendsFromEtcd()
  env = Environment(loader=FileSystemLoader(os.environ.get('MAYFLY_TEMPLATES', '/etc/mayfly/templates')))
  output_filename = os.environ.get('MAYFLY_HAPROXY_CFG', '/etc/haproxy/haproxy.cfg')
  template = env.get_template('haproxy.cfg.jinja')
  with open(output_filename, 'w') as output_file:
    output_file.write(template.render(backends=backends, enumerate=enumerate))

if __name__ == '__main__':

  if args.command == 'update':
    print getFrontendsFromEtcd()
    #updateBackendsFromEtcd()
