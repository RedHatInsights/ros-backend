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
