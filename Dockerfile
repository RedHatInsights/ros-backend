FROM registry.access.redhat.com/ubi8/ubi-minimal

ARG PYTHON_PIP_VERSION=23.3

RUN microdnf install \
    --disableplugin=subscription-manager \
    --nodocs -y python311 tar gzip gcc python3.11-devel libpq-devel

# Install poetry in separate virtual env
ENV POETRY_HOME=/opt/poetry
RUN python -m venv $POETRY_HOME &&\
    $POETRY_HOME/bin/pip install --upgrade pip==$PYTHON_PIP_VERSION setuptools wheel && \
    $POETRY_HOME/bin/pip install poetry

# Set new virtual env for ROS
ENV VIRTUAL_ENV=/app_root/src \
    PATH="/app_root/src/bin:$POETRY_HOME/bin:$PATH"

WORKDIR /app_root/src
COPY pyproject.toml poetry.lock gunicorn.conf.py ./
COPY ros ros

RUN python -m venv $VIRTUAL_ENV && \
    $VIRTUAL_ENV/bin/pip install --upgrade pip==$PYTHON_PIP_VERSION setuptools wheel && \
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
