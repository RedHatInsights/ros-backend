FROM registry.redhat.io/ubi8/ubi-minimal

RUN microdnf install \
    --disableplugin=subscription-manager \
    --nodocs -y python311 tar gzip gcc python3.11-devel libpq-devel

# Install poetry in separate virtual env
ENV POETRY_HOME=/opt/poetry
RUN python -m venv $POETRY_HOME &&\
    $POETRY_HOME/bin/pip install poetry

# Set new virtual env for ROS
ENV VIRTUAL_ENV=/app_root/src \
    PATH="/app_root/src/bin:$POETRY_HOME/bin:$PATH"

WORKDIR /app_root/src
COPY pyproject.toml poetry.lock manage.py seed.py gunicorn.conf.py ./
COPY ros ros
COPY migrations migrations
COPY seed.d seed.d

RUN python -m venv $VIRTUAL_ENV && \
    poetry update pip setuptools wheel && \
    poetry install

LABEL description="The Red Hat Insights resource optimization service \
enables RHEL customers to assess and monitor their public cloud usage \
and optimization. The service exposes workload metrics for CPU, memory, \
and disk-usage and compares them to resource limits recommended by the \
public cloud provider. Currently ROS only provides suggestions for AWS \
RHEL instances. To enable ROS, a customer needs to perform a few \
prerequisite steps on targeted systems via Ansible playbook."
LABEL io.k8s.description="The Red Hat Insights resource optimization service \
enables RHEL customers to assess and monitor their public cloud usage \
and optimization. The service exposes workload metrics for CPU, memory, \
and disk-usage and compares them to resource limits recommended by the \
public cloud provider. Currently ROS only provides suggestions for AWS \
RHEL instances. To enable ROS, a customer needs to perform a few \
prerequisite steps on targeted systems via Ansible playbook."
LABEL io.k8s.display-name="ros-backend"
LABEL io.openshift.tags="ros-backend"
LABEL summary="Image of Resource Optimization Service backend"