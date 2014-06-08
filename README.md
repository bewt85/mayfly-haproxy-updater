mayfly-haproxy-updater
======================

This is part of [mayfly](https://github.com/bewt85/mayfly) which demonstrates the 
concept of testing groups of versions of services in short lived virtual environments.

This is a docker container which mounts the volumes from a [haproxy](https://github.com/bewt85/docker-haproxy) 
container.  It is used to monitor etcd changes and update the mounted `/etc/haproxy/haproxy.cfg` 
accordingly.

It works by adding an `x-mayfly` header to incoming requests to hosts which start with `www-<environment_name>.`. 
The backing services must propogate this header in requests to other services else this wont work.  See the 
[example frontend](https://github.com/bewt85/example-frontend) and [example backend](https://github.com/bewt85/example-backend) 
services for simple python examples.

You can build your own versions of this container by setting the following environment variable 
to your docker index username (if you don't it uses mine) and running this bash script:

```
export DOCKER_ACCOUNT_NAME=<your_name>
sudo -E ./build.sh
```
