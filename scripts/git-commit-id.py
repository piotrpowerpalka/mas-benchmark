import subprocess

def git_sha(default="unknown"):
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return default

print("COMMIT:", git_sha())