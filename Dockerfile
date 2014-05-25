# Docker version 0.11.1

FROM ubuntu:14.04

RUN apt-get update
RUN apt-get install -y python2.7 vim

ADD configure_haproxy.py /usr/local/bin/
ADD haproxy.cfg.bak      /haproxy.cfg.bak 

CMD ["bash"]
#ENTRYPOINT ["/usr/local/bin/configure_haproxy.py"]
