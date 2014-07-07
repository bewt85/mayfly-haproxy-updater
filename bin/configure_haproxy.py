#!/usr/bin/env python

import argparse, cStringIO, hashlib, datetime
from Backend import BackendFactory
from ClassyEtcd import *

parser = argparse.ArgumentParser(description="Tool for updating haproxy.cfg")
parser.add_argument('command', choices=['update'])
args = parser.parse_args()

def uniqueDictsInList(dict_list):
  for i, d in enumerate(dict_list):
    if d not in dict_list[i+1:]:
      yield d

def getBackendsFromEtcd():
  # /mayfly/backends/$SERVICE/$VERSION/$MD5/ip -> Host IP Address
  # /mayfly/backends/$SERVICE/$VERSION/$MD5/port/8080 -> Host port which maps to 8080 
  # /mayfly/backends/$SERVICE/$VERSION/$MD5/env -> Environment which this container supports
  # /mayfly/backends/$SERVICE/$VERSION/$MD5/healthcheck -> URL to hit to check service health (/ping/ping)
  factory = BackendFactory()
  backend_objects = list(factory.fromEtcd())

  backends = {}
  for b in backend_objects:
    for (guest_port, host_port) in b.ports:
      if guest_port == '8080':
        backends.setdefault("%s_%s" % (b.service, b.version), []).append("%s:%s" % (b.host_ip, host_port))

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
