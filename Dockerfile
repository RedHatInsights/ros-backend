FROM registry.redhat.io/rhscl/python-38-rhel7

COPY Pipfile Pipfile.lock manage.py seed.py ${APP_ROOT}/src/

COPY ros ${APP_ROOT}/src/ros/
COPY migrations ${APP_ROOT}/src/migrations/
COPY seed.d ${APP_ROOT}/src/seed.d/
RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --system --deploy --ignore-pipfile
