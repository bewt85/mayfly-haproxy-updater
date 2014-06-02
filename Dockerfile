# Docker version 0.11.1

FROM bewt85/etcdctl:0.4.1 

RUN apt-get update
RUN apt-get install -y python2.7 python-pip python-dev libssl-dev vim git

ADD requirements.txt     /etc/mayfly/
RUN pip install -r       /etc/mayfly/requirements.txt

ADD templates            /etc/mayfly/templates
ADD configure_haproxy.py /usr/local/bin/
ADD haproxy.cfg.bak      /etc/mayfly/haproxy.cfg.bak 

CMD ["bash"]
#ENTRYPOINT ["/usr/local/bin/configure_haproxy.py"]
