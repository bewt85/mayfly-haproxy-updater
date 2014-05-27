# Docker version 0.11.1

FROM bewt85/etcdctl:0.4.1 

RUN apt-get update
RUN apt-get install -y python2.7 vim

RUN wget -O confd_0.3.0_linux_amd64.tar.gz https://github.com/kelseyhightower/confd/releases/download/v0.3.0/confd_0.3.0_linux_amd64.tar.gz
RUN tar -zxvf confd_0.3.0_linux_amd64.tar.gz && mv confd /usr/local/bin/confd

ADD configure_haproxy.py /usr/local/bin/
ADD haproxy.cfg.bak      /haproxy.cfg.bak 
ADD confd_env.sh         /usr/local/bin/

ADD confd /etc/confd
#VOLUME /etc/confd

CMD ["bash"]
#ENTRYPOINT ["/usr/local/bin/configure_haproxy.py"]
