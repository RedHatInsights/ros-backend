FROM registry.redhat.io/rhscl/python-38-rhel7
COPY Pipfile Pipfile.lock manage.py run.py ${APP_ROOT}/src/
COPY ros ${APP_ROOT}/src/ros/
COPY migrations ${APP_ROOT}/src/migrations/
RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --system --deploy --ignore-pipfile
CMD bash -c 'python manage.py db upgrade && python run.py'