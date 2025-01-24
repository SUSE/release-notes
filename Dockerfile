FROM registry.opensuse.org/documentation/containers/containers/opensuse-git-ssh:latest

COPY publish.sh /publish.sh
ENTRYPOINT ["/publish.sh"]
