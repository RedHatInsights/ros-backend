FROM registry.redhat.io/rhel9/pcp:latest

# PEP 440 version specifier for pip (without the "pip" prefix).
# Override must include operators, e.g. ">=26,<27", "==26.1.2", or ">=27,<28".
# A plain version like "27.0" is invalid here.
ARG PYTHON_PIP_SPEC=">=26,<27"

RUN dnf install \
    --nodocs -y python3.11 tar gzip gcc python3.11-devel libpq-devel

# Install poetry in separate virtual env
ARG POETRY_VERSION=2.4.1
ENV POETRY_HOME=/opt/poetry
RUN python3.11 -m venv $POETRY_HOME &&\
    $POETRY_HOME/bin/pip install --upgrade "pip${PYTHON_PIP_SPEC}" setuptools wheel && \
    $POETRY_HOME/bin/pip install "poetry==${POETRY_VERSION}"

# Set new virtual env for ROS
ENV VIRTUAL_ENV=/app_root/src \
    PATH="/app_root/src/bin:$POETRY_HOME/bin:$PATH"

WORKDIR /app_root/src
COPY pyproject.toml poetry.lock manage.py seed.py gunicorn.conf.py ./
COPY ros ros
COPY migrations migrations
COPY seed.d seed.d

RUN python3.11 -m venv $VIRTUAL_ENV && \
    $VIRTUAL_ENV/bin/pip install --upgrade "pip${PYTHON_PIP_SPEC}" setuptools wheel && \
    poetry install

ARG description="The Red Hat Insights resource optimization service \
enables RHEL customers to assess and monitor their public cloud usage \
and optimization. The service exposes workload metrics for CPU, memory, \
and disk-usage and compares them to resource limits recommended by the \
public cloud provider. Currently ROS only provides suggestions for AWS \
RHEL instances. To enable ROS, a customer needs to perform a few \
prerequisite steps on targeted systems via Ansible playbook."

LABEL description=$description \
      io.k8s.description=$description \
      io.k8s.display-name="ros-backend" \
      io.openshift.tags="ros-backend" \
      summary="Image of Resource Optimization Service backend"
