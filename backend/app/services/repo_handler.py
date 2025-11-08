import os
import subprocess
import tempfile
import shutil

# Files we actually care about
IMPORTANT_FILES = [
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "package.json",
    "yarn.lock",
    "Gemfile",
    "go.mod",
    "composer.json",
    "pom.xml",
    "build.gradle",
    ".env.example",
    "Dockerfile",
    ".github/workflows/"
]

def clone_repo_sparse(url: str):
    """
    Clone repo in sparse mode and fetch only important files.
    Returns: dict with files found + temp_dir path.
    """

    temp_dir = tempfile.mkdtemp()

    try:
        # Step 1: Init sparse clone
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", url, temp_dir],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Step 2: Sparse-checkout set only IMPORTANT_FILES
        os.chdir(temp_dir)
        subprocess.run(
            ["git", "sparse-checkout", "set"] + IMPORTANT_FILES,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Step 3: Collect which files we actually got
        collected = []
        for f in IMPORTANT_FILES:
            if os.path.exists(os.path.join(temp_dir, f)):
                collected.append(f)

        return {"cloned_dir": temp_dir, "files_collected": collected}

    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_dir)  # cleanup on fail
        raise RuntimeError(f"Failed to clone repo: {e.stderr.decode()}")

