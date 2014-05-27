#!/bin/bash

extras=""

if [[ ! -z $ETCD_PEERS ]]; then
  extras="-node $ETCD_PEERS $extras"
fi

confd $(echo "$extras $@")
