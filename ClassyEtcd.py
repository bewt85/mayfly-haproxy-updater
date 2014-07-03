import etcd, os 

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
  def rm(self):
    client = getEtcdClient()
    client.delete(self.key, recursive=True)
    self.dir = False
    self.nodes = []
  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default
  def __getitem__(self, key):
    matches = filter(lambda n: n.short_key == key, self.ls())
    if len(matches) > 1:
      raise ValueError("More than one match was found for '%s' in the children on '%s'" % (key, self.key))
    elif len(matches) == 0:
      raise KeyError("Could not find '%s' in the children on '%s'" % (key, self.key))
    else:
      return matches[0]
  def __setitem__(self, key, value):
    client = getEtcdClient()
    client.write(self.key + key, value)
  def __repr__(self):
    if self.value:
      return "%s => %s" % (self.key, self.value)
    else:
      return "\n".join(node.__repr__() for node in self.ls())

