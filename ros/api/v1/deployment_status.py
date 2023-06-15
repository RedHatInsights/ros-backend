import os
import requests
import json

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from kubernetes import config, client
from ros.lib.config import (
    COMMITS_API_URL,
    GITHUB_API_MAXIMUM_RETRIES,
    GITHUB_DEPLOYMENT_BRANCH,
    GITHUB_API_PAGE_SIZE,
)


def get_k8s_data():
    # Load Kubernetes configuration
    config.load_incluster_config()

    # Create a Kubernetes API client
    v1 = client.CoreV1Api()

    pod_name = os.environ.get('HOSTNAME')
    namespace_path = '/var/run/secrets/kubernetes.io/serviceaccount/namespace'
    with open(namespace_path) as f:
        namespace = f.read()

    # Retrieve the pod object data
    pod_data = v1.read_namespaced_pod(name=pod_name, namespace=namespace)

    # Get the pod's initialization time
    init_time = pod_data.status.start_time

    # Get the image tag i.e. commit SHA
    container_image = pod_data.spec.containers[0].image
    image_tag = container_image.split(":")[-1] if ":" in container_image else None
    return init_time, image_tag


class DeploymentStatus:
    """
    Retrieves deployment status information from a GitHub API endpoint.
    It encapsulates methods to interact with the API, handle retries,
    and extract relevant data from the API response.

    Attributes:
        github_commits_api_url (str): The URL of the GitHub API endpoint for retrieving commits.
        pod_start_time (str): The initialization time of the Kubernetes pod.
        pod_sha (str): The SHA of the commit associated with the pod.

    Methods:
        __init__(): Initializes the DeploymentStatus instance.
        __call__(request, *args, **kwargs): Invokes the get() method when class is called as a function.
        make_api_request(): Makes requests using session retries to the GitHub API endpoint, returns the response data.
        get_deployment_data(): Extracts relevant deployment data from the API response.
        get(): Retrieves deployment status JSON.

    Usage:
        deployment_status = DeploymentStatus()
    """

    def __init__(self):
        self.__name__ = "DeploymentStatus"
        self.github_commits_api_url = COMMITS_API_URL
        pod_start_time, pod_sha = get_k8s_data()
        self.pod_start_time = str(pod_start_time)
        self.pod_sha = pod_sha

    def __call__(self):
        return self.get()

    def make_api_request(self):
        headers = {"Accept": "application/vnd.github+json"}
        params = {
            "sha": GITHUB_DEPLOYMENT_BRANCH,
            "per_page": GITHUB_API_PAGE_SIZE,
        }

        # Create a session with retries
        session = requests.Session()
        retry_strategy = Retry(
            total=GITHUB_API_MAXIMUM_RETRIES,  # Number of retries
            backoff_factor=1,  # Delay between retries (exponential backoff)
            status_forcelist=[500, 502, 503, 504, 408, 429]  # HTTP status codes to retry
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)

        # Make a request using the session
        response = session.get(self.github_commits_api_url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
        else:
            data = [{"status": f"Request failed with {response.status_code}. Try again later."}]
        return data

    def get_deployment_data(self):
        deployment_json = {"status": "Request failed, try again later."}
        commits_json = self.make_api_request()
        if "status" in commits_json[0].keys():
            deployment_json = commits_json[0]
        else:
            for item in commits_json:
                if (
                        isinstance(item, dict)
                        and self.pod_sha in item.get("sha", "")
                ):
                    deployment_json = {
                        "branch": GITHUB_DEPLOYMENT_BRANCH,
                        "commit_sha": item.get("sha", ""),
                        "commit_timestamp": item.get("commit", {}).get("committer", {}).get("date", ""),
                        "commit_msg": item.get("commit", {}).get("message", ""),
                        "deployed_at": self.pod_start_time
                    }
                    break
        return deployment_json

    def get(self):
        deployment_status_json = json.dumps(self.get_deployment_data())
        return deployment_status_json
