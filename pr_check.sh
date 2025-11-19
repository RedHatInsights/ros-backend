#!/bin/bash

# --------------------------------------------
# Options that must be configured by app owner
# --------------------------------------------
export APP_NAME="ros"  # name of app-sre "application" folder this component lives in
export COMPONENT_NAME="ros-backend"  # name of app-sre "resourceTemplate" in deploy.yaml for this component
export COMPONENTS="ros-backend"
export IMAGE="quay.io/cloudservices/ros-backend"
export DOCKERFILE="Dockerfile"

# NEW: Dual backend testing logic based on job name
echo "JOB_NAME: $JOB_NAME"

if [[ "$JOB_NAME" == *"ros-backend-v1-pr-tests"* ]]; then
    # Old backend testing configuration
    export ROS_NEW_BACKEND_FLAG_ENABLED="false"
    export IQE_MARKER_EXPRESSION="ros_smoke and (common or old_backend)"
    export IBUTSU_SOURCE="ros-backend-v1-pr"
    echo " Configured for OLD backend testing"
    echo "   - Unleash flag will be set to: FALSE"
    echo "   - Test markers: ros_smoke and (common or old_backend)"
elif [[ "$JOB_NAME" == *"ros-backend-v2-pr-tests"* ]]; then
    # New backend testing configuration
    export ROS_NEW_BACKEND_FLAG_ENABLED="true"
    export IQE_MARKER_EXPRESSION="ros_smoke and (common or new_backend)"
    export IBUTSU_SOURCE="ros-backend-v2-pr"
    echo " Configured for NEW backend testing"
    echo "   - Unleash flag will be set to: TRUE"
    echo "   - Test markers: ros_smoke and (common or new_backend)"
fi

# Standard IQE configuration
export IQE_PLUGINS="ros"
export IQE_FILTER_EXPRESSION=""
export IQE_CJI_TIMEOUT="30m"

# CRITICAL: Pass ROS_NEW_BACKEND_FLAG_ENABLED to IQE via IQE_ENV_VARS
export IQE_ENV_VARS="JOB_NAME=${JOB_NAME},BUILD_NUMBER=${BUILD_NUMBER},BUILD_URL=${BUILD_URL},ROS_NEW_BACKEND_FLAG_ENABLED=${ROS_NEW_BACKEND_FLAG_ENABLED}"

echo "  Final Configuration:"
echo "  IQE_MARKER_EXPRESSION: $IQE_MARKER_EXPRESSION"
echo "  IBUTSU_SOURCE: $IBUTSU_SOURCE"
echo "  IQE_ENV_VARS: $IQE_ENV_VARS"

# Install bonfire repo/initialize
CICD_URL=https://raw.githubusercontent.com/RedHatInsights/bonfire/master/cicd
curl -s $CICD_URL/bootstrap.sh > .cicd_bootstrap.sh && source .cicd_bootstrap.sh

source $CICD_ROOT/build.sh

# Deploy ros to an ephemeral namespace for testing
source $CICD_ROOT/deploy_ephemeral_env.sh

# Run iqe-ros smoke tests with ClowdJobInvocation
source $CICD_ROOT/cji_smoke_test.sh
