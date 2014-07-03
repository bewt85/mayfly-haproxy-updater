#!/usr/bin/env python

import argparse
import os, re, cStringIO
import hashlib
import datetime

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
  def __getitem__(self, key):
    matches = filter(lambda n: n.short_key == key, self.ls())
    if len(matches) > 1:
      raise ValueError("More than one match was found for '%s' in the children on '%s'" % (key, self.key))
    elif len(matches) == 0:
      raise KeyError("Could not find '%s' in the children on '%s'" % (key, self.key))
    else:
      return matches[0]
  def __repr__(self):
    if self.value:
      return "%s => %s" % (self.key, self.value)
    else:
      return "\n".join(node.__repr__() for node in self.ls())

def getBackendsFromEtcd():
  client = getEtcdClient()
  backends = {}
  for backend in (Node(**n) for n in client.read('/mayfly/backends', recursive=True)._children):
    for version in backend.ls():
      for host in version.ls():
        backends.setdefault("%s_%s" % (backend.short_key, version.short_key), []).append(host.value) 
  return backends

def getFrontendsFromEtcd():
  client = getEtcdClient()
  # /mayfly/environments/<name>/prefix                       => www
  # /mayfly/environments/<name>/header                       => prod
  # /mayfly/environments/<name>/routes/*                     => frontend/0.0.1
  # /mayfly/environments/<name>/services/<service>/<version> => 0
  environments = {}
  for environment in (Node(**n) for n in client.read('/mayfly/environments', recursive=True)._children):
    (env_name, prefix, header) = (environment.short_key, None, None)
    prefix = environment['prefix'].value
    environments.setdefault('prefixes', []).append(prefix)
    header = environment['header'].value
    environments.setdefault('environments', []).append({'env_name': env_name, 'env_prefix': prefix, 'env_header': header})
    for service in environment['services'].ls():
      service_name = service.short_key
      environments.setdefault('services', []).append(service_name)
      version = service.ls()[0].short_key
      if len(service.ls())> 1:
        raise ValueError("Etcd returns more than one version of %s in the $s environment.  Aborting" % (service_name, env_name))
      environments.setdefault('backends', []).append({'env_name': env_name, 'version': version, 'service_name': service_name})
    www_service, www_version = environment['routes']['*'].value.split('/') # Could support more routes later
    environments.setdefault('routes', []).append({'env_name': env_name, 'route': '', 'service': www_service, 'version': www_version})
  return {80: environments}

from jinja2 import Environment, FileSystemLoader

def updateHaproxyConfigFromEtcd():
  backends = getBackendsFromEtcd()
  frontends = getFrontendsFromEtcd()
  env = Environment(loader=FileSystemLoader(os.environ.get('MAYFLY_TEMPLATES', '/etc/mayfly/templates')))
  output_filename = os.environ.get('MAYFLY_HAPROXY_CFG', '/etc/haproxy/haproxy.cfg')
  template = env.get_template('haproxy.cfg.jinja')
  revised_config=template.render(frontends=frontends, backends=backends, enumerate=enumerate)
  new_hash=hashlib.md5()
  new_hash.update(revised_config)
  with open(output_filename, 'r') as output_file:
    old_hash=hashlib.md5()
    old_hash.update(output_file.read())
  if new_hash.digest() == old_hash.digest():
    print "[INFO %s] Not updating HAProxy config - no changes made" % datetime.datetime.now()
  else: 
    print "[INFO %s] Updating HAProxy config" % datetime.datetime.now()
    with open(output_filename, 'w') as output_file:
      output_file.write(template.render(frontends=frontends, backends=backends, enumerate=enumerate))

if __name__ == '__main__':

  if args.command == 'update':
    updateHaproxyConfigFromEtcd()
