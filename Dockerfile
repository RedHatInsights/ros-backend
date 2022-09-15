FROM registry.redhat.io/ubi8/ubi-minimal

WORKDIR /app_root/src

COPY Pipfile Pipfile.lock manage.py seed.py gunicorn.conf.py ./

RUN microdnf install --disableplugin=subscription-manager --nodocs -y python38 tar gzip

COPY ros ros
COPY migrations migrations
COPY seed.d seed.d

RUN pip3 install --upgrade pip setuptools wheel && \
    pip3 install pipenv && \
    pipenv install --system --deploy --ignore-pipfile
