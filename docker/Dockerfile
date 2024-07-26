FROM registry.access.redhat.com/ubi8/ubi:8.9-1136

ENV LOG_LEVEL=INFO
ARG USER=ait
ARG GROUP=ait
ARG UID=1001
ARG GID=1001
ARG HOME=/home/$USER
ENV PROJECT_HOME=/home/$USER

RUN dnf install -y python3.9 python3-pip \
    && yum install -y nc \
    && groupadd -r -g ${GID} ${GROUP} \
    && useradd -m -u ${UID} -g ${GROUP} ${USER}

USER ait
WORKDIR $PROJECT_HOME
COPY --chown=${USER}:${GROUP} . $PROJECT_HOME/AIT-Core
RUN python3.9 -m pip install --user --upgrade pip setuptools virtualenvwrapper virtualenv poetry \
    && echo 'export PATH="${PROJECT_HOME}/.local/bin:$PATH"' >> ~/.bashrc \
    && echo 'export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3.9' >> ~/.bashrc \
    && echo 'export WORKON_HOME=${PROJECT_HOME}/.virtualenvs' >> ~/.bashrc \
    && echo 'export PROJECT_HOME=${PROJECT_HOME}' >> ~/.bashrc \
    && echo 'export VIRTUALENVWRAPPER_VIRTUALENV=${PROJECT_HOME}/.local/bin/virtualenv' >> ~/.bashrc \
    && echo 'source ${PROJECT_HOME}/.local/bin/virtualenvwrapper.sh' >> ~/.bashrc \
    && source ~/.bashrc \
    && cd $PROJECT_HOME \
    && echo 'if [ $VIRTUAL_ENV ==  "${PROJECT_HOME}/.virtualenvs/ait" ]; then' >> $PROJECT_HOME/.virtualenvs/postactivate \
    && echo 'export AIT_ROOT=${PROJECT_HOME}/AIT-Core' >> $PROJECT_HOME/.virtualenvs/postactivate \
    && echo 'export AIT_CONFIG=${PROJECT_HOME}/AIT-Core/docker/network-test-config.yaml' >> $PROJECT_HOME/.virtualenvs/postactivate \
    && echo 'fi' >> $PROJECT_HOME/.virtualenvs/postactivate \
    && cd AIT-Core \
    && mkvirtualenv ait \
    && poetry install
ENTRYPOINT ["/usr/bin/bash","-c"]
CMD ["source /home/ait/.bashrc && cd AIT-Core && workon ait && ait-server"]
#CMD ["sleep infinity"]
