# app/api/routes.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
import re
import importlib

from app.services.repo_handler import clone_repo_sparse
from app.services.docker_optimizer import create_optimized_dockerfile_and_report
aws_deployer = importlib.import_module("app.services.aws_deployer")

from app.supabase_client import supabase
from app.utils.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import StreamingResponse

# ⬇️ include sub-routers so /auth/* and profile endpoints are registered
from app.api.auth import router as auth_router
from app.api.profile import router as profile_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(profile_router)

# Correct token URL (for docs + OAuth flow)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class RepoRequest(BaseModel):
    repo_url: HttpUrl


# -------------------- Submit Repo --------------------
@router.post("/submit-repo/")
def submit_repo(request: RepoRequest, token: str = Depends(oauth2_scheme)):
    # Supabase guard (friendly error if not configured)
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    url = str(request.repo_url)

    # Validate GitHub repo format
    pattern = r"^https:\/\/github\.com\/[\w\-]+\/[\w\-]+(?:\.git)?$"
    if not re.match(pattern, url):
        raise HTTPException(
            status_code=400,
            detail="Invalid repo URL. Expected format: https://github.com/user/repo"
        )

    # Decode JWT to get user_id
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not found in token")

    try:
        # Check if repo already exists for this user
        existing = (
            supabase.table("repos")
            .select("*")
            .eq("user_id", user_id)
            .eq("repo_link", url)
            .execute()
        )

        if existing.data:  # if repo already stored
            return {
                "received_repo": url,
                "status": "already stored in database",
                "files_collected": "skipped (repo already cloned)"
            }

        # Otherwise, clone and insert
        result = clone_repo_sparse(url)

        repo_row = {
            "user_id": user_id,
            "repo_link": url,
        }
        inserted_repo = supabase.table("repos").insert(repo_row).execute()
        repo_id = inserted_repo.data[0]["id"]

        # Generate optimized Dockerfile or docker-compose.yml
        artifact = create_optimized_dockerfile_and_report(url)

        artifact_row = {
            "repo_id": repo_id,
            "dockerfile": artifact["dockerfile"],
            "report": artifact["report"],
            "ci_cd_instructions": artifact["ci_cd_instructions"],
            "workflow_file": artifact["workflow_file"]
        }

        # Store artifact in DB
        supabase.table("artifacts").insert(artifact_row).execute()

        return {
            "received_repo": url,
            "status": "repo + artifact stored successfully",
            "files_collected": result["files_collected"],
            "artifact": {
                "dockerfile_or_compose": (artifact["dockerfile"] or "")[:100] + "...",
                "report": artifact["report"]
            }
        }

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Deploy to AWS (live streaming) --------------------
@router.get("/deploy-aws/{repo_id}")
def deploy_aws(repo_id: int, token: str = Depends(oauth2_scheme)):
    # Supabase guard
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    # Decode JWT
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not found in token")

    # Fetch artifact from Supabase
    artifact_res = (
        supabase.table("artifacts")
        .select("*")
        .eq("repo_id", repo_id)
        .execute()
    )

    if not artifact_res.data:
        raise HTTPException(status_code=404, detail="Artifact not found")

    artifact = artifact_res.data[0]

    def log_generator():
        deploy_func = None
        for name in ("deploy_to_aws", "deploy", "stream_deploy_to_aws"):
            if hasattr(aws_deployer, name):
                deploy_func = getattr(aws_deployer, name)
                break

        if deploy_func is None:
            yield "[error] aws_deployer has no deploy function (expected one of: deploy_to_aws, deploy, stream_deploy_to_aws)."
            return

        for log_line in deploy_func(
            dockerfile_text=artifact.get("dockerfile") or "",
            image_tag=f"user-{user_id}-repo-{repo_id}",
            repo_name=f"repo-{repo_id}",
        ):
            yield f"{log_line}\n"

    return StreamingResponse(log_generator(), media_type="text/plain")
