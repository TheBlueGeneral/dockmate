import os
import shutil
import subprocess
import tempfile
import time
from typing import Dict, Optional, Generator

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from app.supabase_client import supabase

# Load .env
load_dotenv()

# --- AWS clients ------------------------------------------------------------
session = boto3.session.Session()
ecr_client = session.client("ecr")
ecs_client = session.client("ecs")
logs_client = session.client("logs")


# --- Helpers ----------------------------------------------------------------

def safe_run(cmd: list, cwd: Optional[str] = None) -> Dict:
    try:
        proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return {"ok": proc.returncode == 0, "out": proc.stdout.decode(), "err": proc.stderr.decode()}
    except Exception as e:
        return {"ok": False, "out": "", "err": str(e)}


def build_docker_image(dockerfile_dir: str, tag: str) -> Dict:
    cmd = ["docker", "build", "-t", tag, "."]
    return safe_run(cmd, cwd=dockerfile_dir)


def push_to_ecr(local_tag: str, ecr_repo: str) -> str:
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    region = boto3.session.Session().region_name
    ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{ecr_repo}:latest"

    auth_token = ecr_client.get_authorization_token()
    token = auth_token['authorizationData'][0]['authorizationToken']
    proxy_endpoint = auth_token['authorizationData'][0]['proxyEndpoint']
    safe_run(["docker", "login", "-u", "AWS", "-p", token, proxy_endpoint])

    try:
        ecr_client.describe_repositories(repositoryNames=[ecr_repo])
    except ClientError:
        ecr_client.create_repository(repositoryName=ecr_repo)

    safe_run(["docker", "tag", local_tag, ecr_uri])
    push_res = safe_run(["docker", "push", ecr_uri])
    if not push_res["ok"]:
        raise RuntimeError(f"ECR push failed: {push_res['err']}")
    return ecr_uri


def run_fargate_task(ecr_uri: str, cluster_name: str, task_name: str, log_group: str) -> Dict:
    try:
        logs_client.create_log_group(logGroupName=log_group)
    except ClientError:
        pass

    task_def = ecs_client.register_task_definition(
        family=task_name,
        networkMode="awsvpc",
        containerDefinitions=[
            {
                "name": task_name,
                "image": ecr_uri,
                "essential": True,
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": log_group,
                        "awslogs-region": boto3.session.Session().region_name,
                        "awslogs-stream-prefix": task_name
                    }
                },
                "memory": 512,
                "cpu": 256,
            }
        ],
        requiresCompatibilities=["FARGATE"],
        memory="512",
        cpu="256",
        executionRoleArn=f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/ecsTaskExecutionRole"
    )
    task_def_arn = task_def["taskDefinition"]["taskDefinitionArn"]

    run_res = ecs_client.run_task(
        cluster=cluster_name,
        taskDefinition=task_def_arn,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": ["subnet-xxxxxx"],  # replace with your subnet
                "assignPublicIp": "ENABLED"
            }
        }
    )
    task_arn = run_res["tasks"][0]["taskArn"]
    return {"task_arn": task_arn, "log_group": log_group, "task_name": task_name}


def stream_cloudwatch_logs(log_group: str, stream_prefix: str, poll_interval: float = 3.0) -> Generator[str, None, None]:
    """Yield logs in real-time as they appear."""
    seen_events = set()
    while True:
        streams = logs_client.describe_log_streams(
            logGroupName=log_group,
            logStreamNamePrefix=stream_prefix,
            orderBy="LastEventTime",
            descending=True
        )["logStreams"]

        if not streams:
            time.sleep(poll_interval)
            continue

        stream_name = streams[0]["logStreamName"]
        events = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startFromHead=True
        )["events"]

        new_events = [e["message"] for e in events if e["eventId"] not in seen_events]
        for e in events:
            seen_events.add(e["eventId"])

        for msg in new_events:
            yield msg

        time.sleep(poll_interval)


# --- Main deployer ----------------------------------------------------------

def deploy_repo_to_aws(repo_id: int) -> Generator[str, None, None]:
    artifact_res = supabase.table("artifacts").select("*").eq("repo_id", repo_id).execute()
    if not artifact_res.data:
        raise RuntimeError(f"No artifact found for repo_id {repo_id}")

    artifact = artifact_res.data[0]
    dockerfile_content = artifact.get("dockerfile") or artifact.get("docker_compose")
    if not dockerfile_content:
        raise RuntimeError("No Dockerfile or docker-compose content found for deployment")

    temp_dir = tempfile.mkdtemp()
    dockerfile_path = os.path.join(temp_dir, "Dockerfile")
    with open(dockerfile_path, "w", encoding="utf-8") as f:
        f.write(dockerfile_content)

    local_tag = f"repo-{repo_id}:latest"
    build_res = build_docker_image(temp_dir, local_tag)
    if not build_res["ok"]:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Docker build failed: {build_res['err']}")

    ecr_repo = f"repo-{repo_id}"
    ecr_uri = push_to_ecr(local_tag, ecr_repo)

    cluster_name = "dockmate-demo-cluster"
    task_name = f"repo-{repo_id}-task"
    log_group = f"/dockmate/repo-{repo_id}"
    run_res = run_fargate_task(ecr_uri, cluster_name, task_name, log_group)

    # Stream logs in real-time
    try:
        for log_line in stream_cloudwatch_logs(log_group, task_name):
            yield log_line
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

