#!/bin/bash

# --------------------------------------------
# Options that must be configured by app owner
# --------------------------------------------
export APP_NAME="ros"  # name of app-sre "application" folder this component lives in
export COMPONENT_NAME="ros-backend"  # name of app-sre "resourceTemplate" in deploy.yaml for this component
export COMPONENTS="ros-backend"
export IMAGE="quay.io/cloudservices/ros-backend"
export DOCKERFILE="Dockerfile"

# NEW: Backend version selection logic
BACKEND_VERSION=${BACKEND_VERSION:-"old"}

if [ "$BACKEND_VERSION" = "old" ]; then
    export IQE_MARKER_EXPRESSION="ros_smoke and (common or old_backend)"
    export IBUTSU_SOURCE="ros-old-backend-pr"
elif [ "$BACKEND_VERSION" = "new" ]; then
    export IQE_MARKER_EXPRESSION="ros_smoke and (common or new_backend)"
    export IBUTSU_SOURCE="ros-new-backend-pr"
else
    # Default fallback
    export IQE_MARKER_EXPRESSION="ros_smoke"
    export IBUTSU_SOURCE="ros-backend-pr"
fi

export IQE_PLUGINS="ros"
export IQE_FILTER_EXPRESSION=""
export IQE_CJI_TIMEOUT="30m"
export IQE_ENV_VARS="JOB_NAME=${JOB_NAME},BUILD_NUMBER=${BUILD_NUMBER},BUILD_URL=${BUILD_URL}"
export EXTRA_DEPLOY_ARGS="--set-parameter ros-backend/BACKEND_VERSION=${BACKEND_VERSION}"

# Install bonfire repo/initialize
CICD_URL=https://raw.githubusercontent.com/RedHatInsights/bonfire/master/cicd
curl -s $CICD_URL/bootstrap.sh > .cicd_bootstrap.sh && source .cicd_bootstrap.sh

source $CICD_ROOT/build.sh

# Deploy ros to an ephemeral namespace for testing
source $CICD_ROOT/deploy_ephemeral_env.sh

# Run iqe-ros somke tests with ClowdJobInvocation
source $CICD_ROOT/cji_smoke_test.sh

