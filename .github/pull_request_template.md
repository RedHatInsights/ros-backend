## PR Title :boom:

Please title this PR with a summary of the change, along with the JIRA card number.

Suggested formats: 

1. Fixes/Refs #RHIROS-XXX - Title
2. RHIROS-XXX Title 

Feel free to remove this section from PR description once done.

## Why do we need this change? :thought_balloon:

Please include the __context of this change__ here.

## Documentation update? :memo:

- [ ] Yes
- [ ] No

## Security Checklist :lock:

Upon raising this PR please go through [RedHatInsights/secure-coding-checklist](https://github.com/RedHatInsights/secure-coding-checklist)

## :guardsman: Checklist :dart:

- [ ] Bugfix
- [ ] New Feature
- [ ] Refactor
- [ ] Unittests Added
- [ ] DRY code
- [ ] Dependency Added
- [ ] DB Migration Added

## ROS RHEL Github label usage for executing a desired test suit
   
   Add one of these labels to a pull request to control which ROS RHEL backend tests to run:
     Available ROS RHEL labels:
       1. test-backend-v1:
          IQE markers used: ros_smoke and insights_ros_v1
          description: Runs only ROS RHEL old backend tests
       2. test-backend-v2:
          IQE markers used: ros_smoke and insights_ros_v2
          description: Runs only ROS RHEL new backend tests
       3. test-backend-both:
          IQE markers used: ros_smoke
          description: Runs all ROS RHEL backend tests  

   How to use for ROS RHEL testing:
     1. Add a label to ROS backend pull request using GitHub's label interface
     2. ROS RHEL tests execute automatically on new commits, and users can add labels either right before or right after commits are pushed.
     3. Tests will be executed as per label

  Example:
     1. User pushed a commit 'ABC' . 
        Label added : test-backend-v1 ( No matter if added right before or after a commit )
        Remove other labels
        ROS RHEL Old backend tests will get executed
     2. User pushed a commit 'XYZ' .
        Label added: test-backend-v2 ( No matter if added right before or after a commit )
        Remove other labels
        ROS RHEL New backend tests will get executed
     3. User pushed a commit 'PQR' .
        Label added: test-backend-both ( No matter if added right before or after a commit )
        Remove other labels
        ROS RHEL both backends tests i.e. all tests will get executed
     4. User pushed a commit 'LMN'
        No label is present on PR.
        ROS RHEL all tests will get executed
    
   Limitations:
       1. Changing labels on the same PR with the same commit will not trigger new tests.
          Example:
          User pushed a commit 'EFG'
          label added: test-backend-v1 => Old backend tests will get executed
          Now label added : test-backend-v2 AND label removed: test-backend-v1 => New backend tests won't be executed
               	   
## Additional :mega:

Feel free to add any other relevant details such as __links, notes, screenshots__, here.
