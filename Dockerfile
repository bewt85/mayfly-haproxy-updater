# Docker version 0.11.1

FROM bewt85/etcdctl:0.4.1 

RUN apt-get update # Updated 2014-07-06
RUN apt-get install -y python2.7 python-dev libssl-dev vim git wget
RUN wget https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py && python /tmp/get-pip.py

ADD requirements.txt     /etc/mayfly/
RUN pip install -r       /etc/mayfly/requirements.txt

ADD templates            /etc/mayfly/templates
ADD bin/                 /usr/local/bin/
ADD haproxy.cfg.bak      /etc/mayfly/haproxy.cfg.bak 

CMD ["bash"]
#ENTRYPOINT ["/usr/local/bin/configure_haproxy.py"]
