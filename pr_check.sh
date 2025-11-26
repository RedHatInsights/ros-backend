#!/bin/bash

export APP_NAME="ros"
export COMPONENT_NAME="ros-backend"
export COMPONENTS="ros-backend"
export IMAGE="quay.io/cloudservices/ros-backend"
export DOCKERFILE="Dockerfile"

echo "=== JOB INFORMATION ==="
echo "JOB_NAME: $JOB_NAME"
echo "BUILD_NUMBER: $BUILD_NUMBER"
echo "GitHub PR ID: $ghprbPullId"

get_pr_labels() {
    if [[ -n "$ghprbPullId" && -n "$GITHUB_TOKEN" ]]; then
        echo "Fetching PR labels from GitHub API..."
        local labels=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
            "https://api.github.com/repos/RedHatInsights/ros-backend/pulls/$ghprbPullId" | \
            jq -r '.labels[].name' 2>/dev/null || echo "")
        echo "PR Labels: $labels"
        echo "$labels"
    else
        echo "GitHub token or PR ID not available for label fetching"
        echo ""
    fi
}

PR_LABELS=$(get_pr_labels)

echo "=== LABEL DETECTION ==="
echo "Detected Labels: $PR_LABELS"

if [[ -n "$PR_LABELS" ]] && echo "$PR_LABELS" | grep -q "test-backend-v1"; then
    echo "=== V1 BACKEND TESTING ==="
    export ROS_BACKEND_V2_FLAG_ENABLED="false"
    export IQE_MARKER_EXPRESSION="ros_smoke and insights_ros_v1"
    export IBUTSU_SOURCE="ros-backend-v1-pr"

elif [[ -n "$PR_LABELS" ]] && echo "$PR_LABELS" | grep -q "test-backend-v2"; then
    echo "=== V2 BACKEND TESTING ==="
    export ROS_BACKEND_V2_FLAG_ENABLED="true"
    export IQE_MARKER_EXPRESSION="ros_smoke and insights_ros_v2"
    export IBUTSU_SOURCE="ros-backend-v2-pr"

elif [[ -n "$PR_LABELS" ]] && echo "$PR_LABELS" | grep -q "test-backend-both"; then
    echo "=== BOTH BACKENDS TESTING ==="
    export ROS_BACKEND_V2_FLAG_ENABLED="auto"
    export IQE_MARKER_EXPRESSION="ros_smoke"
    export IBUTSU_SOURCE="ros-backend-both-pr"

else
    echo "=== NORMAL PR CHECK ==="
    export IQE_MARKER_EXPRESSION="ros_smoke"
    export IBUTSU_SOURCE="ros-backend-pr"
fi

export IQE_PLUGINS="ros"
export IQE_FILTER_EXPRESSION=""
export IQE_CJI_TIMEOUT="30m"

export IQE_ENV_VARS="JOB_NAME=${JOB_NAME},BUILD_NUMBER=${BUILD_NUMBER},BUILD_URL=${BUILD_URL}"

if [[ -n "$ROS_BACKEND_V2_FLAG_ENABLED" ]]; then
    export IQE_ENV_VARS="${IQE_ENV_VARS},ROS_BACKEND_V2_FLAG_ENABLED=${ROS_BACKEND_V2_FLAG_ENABLED}"
fi

echo "=== FINAL CONFIGURATION ==="
echo "IQE_MARKER_EXPRESSION: $IQE_MARKER_EXPRESSION"
echo "IBUTSU_SOURCE: $IBUTSU_SOURCE"
echo "IQE_ENV_VARS: $IQE_ENV_VARS"

CICD_URL=https://raw.githubusercontent.com/RedHatInsights/bonfire/master/cicd
curl -s $CICD_URL/bootstrap.sh > .cicd_bootstrap.sh && source .cicd_bootstrap.sh

source $CICD_ROOT/build.sh
source $CICD_ROOT/deploy_ephemeral_env.sh
source $CICD_ROOT/cji_smoke_test.sh
