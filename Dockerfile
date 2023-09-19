FROM ubuntu:20.04

# install dependencies
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN apt-get install -y python3-tk
RUN apt-get install -y vim
RUN apt-get install -y tmux

# add user
RUN useradd -ms /bin/bash benchmarker
USER benchmarker

# setup environment
COPY --chown=benchmarker . /home/benchmarker/DMFsim-benchmarking
WORKDIR /home/benchmarker/DMFsim-benchmarking
RUN pip install .
RUN test -d ~/.config/procps || mkdir -p ~/.config/procps
RUN cp ./toprc ~/.config/procps

