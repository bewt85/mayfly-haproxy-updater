#!/usr/bin/env python

import argparse, cStringIO
import datetime
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
  """
  /mayfly/backends/$SERVICE/$VERSION/$MD5/ip -> Host IP Address
  /mayfly/backends/$SERVICE/$VERSION/$MD5/port/8080 -> Host port which maps to 8080 
  /mayfly/backends/$SERVICE/$VERSION/$MD5/env -> Environment which this container supports
  /mayfly/backends/$SERVICE/$VERSION/$MD5/healthcheck -> URL to hit to check service health (/ping/ping)
  """
  client = getEtcdClient()
  backends = {}
  for backend in (Node(**n) for n in client.read('/mayfly/backends', recursive=True)._children):
    for version in backend.ls():
      for host in version.ls():
        backends.setdefault("%s_%s" % (backend.short_key, version.short_key), []).append(host.value) 
  return backends

def getFrontendsFromEtcd():
  # /mayfly/backends/$SERVICE/$VERSION/$MD5/ip -> Host IP Address
  # /mayfly/backends/$SERVICE/$VERSION/$MD5/port/8080 -> Host port which maps to 8080 
  # /mayfly/backends/$SERVICE/$VERSION/$MD5/env -> Environment which this container supports
  # /mayfly/backends/$SERVICE/$VERSION/$MD5/healthcheck -> URL to hit to check service health (/ping/ping)
  factory = BackendFactory()
  backend_objects = list(factory.fromEtcd())

  environments = list(uniqueDictsInList(map(lambda b: {'env_name': b.env, 'env_prefix': "www-%s" % b.env, 'env_header': b.env}, backend_objects)))
  services = list(set(map(lambda b: b.service, backend_objects)))
  backends = list(uniqueDictsInList(map(lambda b: {'env_name': b.env, 'version': b.version, 'service_name': b.service}, backend_objects)))
  routes =  list(uniqueDictsInList(map(lambda b: {'env_name': b.env, 'route': '', 'service': b.service, 'version': b.version}, backend_objects)))
  return {80: {'environments': environments, 'services': services, 'backends': backends, 'routes': routes}}

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
