#!/bin/bash

export APP_NAME="ros"
export COMPONENT_NAME="ros-backend"
export COMPONENTS="ros-backend"
export IMAGE="quay.io/cloudservices/ros-backend"
export DOCKERFILE="Dockerfile"

echo "JOB_NAME: $JOB_NAME"
echo "GitHub Comment: $ghprbCommentBody"

if [[ "$ghprbCommentBody" == *"[test-backend-v1]"* ]]; then
    export ROS_BACKEND_V2_FLAG_ENABLED="false"
    export IQE_MARKER_EXPRESSION="ros_smoke and insights_ros_v1"
    export IBUTSU_SOURCE="ros-backend-v1-pr"
    echo "Configured for v1 backend testing"
    echo "   - Unleash flag will be set to: FALSE"
    echo "   - Test markers: ros_smoke and insights_ros_v1"
elif [[ "$ghprbCommentBody" == *"[test-backend-v2]"* ]]; then
    export ROS_BACKEND_V2_FLAG_ENABLED="true"
    export IQE_MARKER_EXPRESSION="ros_smoke and insights_ros_v2"
    export IBUTSU_SOURCE="ros-backend-v2-pr"
    echo "Configured for v2 backend testing"
    echo "   - Unleash flag will be set to: TRUE"
    echo "   - Test markers: ros_smoke and insights_ros_v2"
else
    export IQE_MARKER_EXPRESSION=""
    export IBUTSU_SOURCE="ros-backend-pr"
    echo "Normal PR check configuration"
fi

export IQE_PLUGINS="ros"
export IQE_FILTER_EXPRESSION=""
export IQE_CJI_TIMEOUT="30m"

export IQE_ENV_VARS="JOB_NAME=${JOB_NAME},BUILD_NUMBER=${BUILD_NUMBER},BUILD_URL=${BUILD_URL}"

if [[ -n "$ROS_BACKEND_V2_FLAG_ENABLED" ]]; then
    export IQE_ENV_VARS="${IQE_ENV_VARS},ROS_BACKEND_V2_FLAG_ENABLED=${ROS_BACKEND_V2_FLAG_ENABLED}"
fi

echo "Final Configuration:"
echo "  IQE_MARKER_EXPRESSION: $IQE_MARKER_EXPRESSION"
echo "  IBUTSU_SOURCE: $IBUTSU_SOURCE"
echo "  IQE_ENV_VARS: $IQE_ENV_VARS"

CICD_URL=https://raw.githubusercontent.com/RedHatInsights/bonfire/master/cicd
curl -s $CICD_URL/bootstrap.sh > .cicd_bootstrap.sh && source .cicd_bootstrap.sh

source $CICD_ROOT/build.sh
source $CICD_ROOT/deploy_ephemeral_env.sh
source $CICD_ROOT/cji_smoke_test.sh
