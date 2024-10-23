# FROM redhat/ubi8:latest

# ENV LOG_LEVEL=INFO
# ARG USER=ait
# ARG GROUP=ait
# ARG UID=1001
# ARG GID=1001
# ARG HOME=/home/$USER
# ENV PROJECT_HOME=/home/$USER

# RUN dnf install -y python3.9 python3-pip \
#     && yum install -y nc \
#     && groupadd -r -g ${GID} ${GROUP} \
#     && useradd -m -u ${UID} -g ${GROUP} ${USER}

# USER ait
# WORKDIR $PROJECT_HOME
# COPY --chown=${USER}:${GROUP} . $PROJECT_HOME/AIT-Core
# RUN python3.9 -m pip install --user --upgrade pip setuptools virtualenvwrapper virtualenv poetry \
#     && echo 'export PATH="${PROJECT_HOME}/.local/bin:$PATH"' >> ~/.bashrc \
#     && echo 'export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3.9' >> ~/.bashrc \
#     && echo 'export WORKON_HOME=${PROJECT_HOME}/.virtualenvs' >> ~/.bashrc \
#     && echo 'export PROJECT_HOME=${PROJECT_HOME}' >> ~/.bashrc \
#     && echo 'export VIRTUALENVWRAPPER_VIRTUALENV=${PROJECT_HOME}/.local/bin/virtualenv' >> ~/.bashrc \
#     && echo 'source ${PROJECT_HOME}/.local/bin/virtualenvwrapper.sh' >> ~/.bashrc \
#     && source ~/.bashrc \
#     && cd $PROJECT_HOME \
#     && echo 'if [ $VIRTUAL_ENV ==  "${PROJECT_HOME}/.virtualenvs/ait" ]; then' >> $PROJECT_HOME/.virtualenvs/postactivate \
#     && echo 'export AIT_ROOT=${PROJECT_HOME}/AIT-Core' >> $PROJECT_HOME/.virtualenvs/postactivate \
#     && echo 'export AIT_CONFIG=${PROJECT_HOME}/AIT-Core/docker/network-test-config.yaml' >> $PROJECT_HOME/.virtualenvs/postactivate \
#     && echo 'fi' >> $PROJECT_HOME/.virtualenvs/postactivate \
#     && cd AIT-Core \
#     && mkvirtualenv ait \
#     && poetry install
# ENTRYPOINT ["/usr/bin/bash","-c"]
# CMD ["source /home/ait/.bashrc && cd AIT-Core && workon ait && ait-server"]
#CMD ["sleep infinity"]


FROM redhat/ubi8:latest

ENV LOG_LEVEL=INFO
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PROJECT_HOME=/AIT-Core

RUN dnf install -y python3.9 python3-pip \
    && yum install -y nc \
    && ln -sf /usr/bin/python3.9 /usr/bin/python

WORKDIR $PROJECT_HOME
RUN python3.9 -m pip install --upgrade pip setuptools poetry
COPY poetry.lock pyproject.toml $PROJECT_HOME/

# Cache the install of all deps except for the root module
WORKDIR $PROJECT_HOME/
RUN poetry install --no-interaction --no-ansi --no-root

WORKDIR $PROJECT_HOME
COPY ait $PROJECT_HOME/ait
COPY config $PROJECT_HOME/config
COPY doc $PROJECT_HOME/doc
COPY docker $PROJECT_HOME/docker
COPY openmct $PROJECT_HOME/openmct
COPY poetry_cli $PROJECT_HOME/poetry_cli
COPY scripts $PROJECT_HOME/scripts
COPY sequences $PROJECT_HOME/sequences
COPY README.rst $PROJECT_HOME/
COPY setup.cfg $PROJECT_HOME/tests
RUN echo 'export AIT_ROOT=${PROJECT_HOME}' >> ~/.bashrc \
    && echo 'export AIT_CONFIG=${PROJECT_HOME}/docker/network-test-config.yaml' >> ~/.bashrc \
    && echo 'export POETRY_VIRTUALENVS_CREATE=false' >> ~/.bashrc \
    && poetry install --no-interaction --no-ansi
ENTRYPOINT ["/usr/bin/bash","-c"]
#CMD ["source ~/.bashrc && ait-server"]

# FROM redhat/ubi8:latest

# ENV LOG_LEVEL=INFO
# ENV PROJECT_HOME=/AIT-Core
# ENV POETRY_VIRTUALENVS_CREATE=false
# RUN dnf install -y python3.9 python3-pip \
#     && yum install -y nc \
#     && ln -sf /usr/bin/python3.9 /usr/bin/python

# WORKDIR $PROJECT_HOME
# RUN python3.9 -m pip install --upgrade pip setuptools poetry
# COPY poetry.lock pyproject.toml $PROJECT_HOME/

# # Cache the install of all deps except for the root module
# WORKDIR $PROJECT_HOME
# RUN poetry install --no-interaction --no-ansi --no-root

# WORKDIR $PROJECT_HOME
# COPY ait $PROJECT_HOME/ait
# COPY docker $PROJECT_HOME/docker
# COPY scripts $PROJECT_HOME/scripts
# COPY config $PROJECT_HOME/config
# RUN echo 'export PATH="${PROJECT_HOME}/.local/bin:$PATH"' >> ~/.bashrc \
#     && echo 'export AIT_ROOT=${PROJECT_HOME}' >> ~/.bashrc \
#     && echo 'export AIT_CONFIG=${PROJECT_HOME}/docker/network-test-config.yaml' >> ~/.bashrc \
#     && echo 'export POETRY_VIRTUALENVS_CREATE=false' >> ~/.bashrc \
#     && poetry install --no-interaction --no-ansi
# ENTRYPOINT ["/usr/bin/bash","-c"]
