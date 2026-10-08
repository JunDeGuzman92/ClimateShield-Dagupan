"""Publish the offline field pack (field/) to GitHub Pages as the gh-pages branch.

Run after changing any file in field/:   python publish_field.py
The first run also needs the Pages feature switched on:
    gh api -X POST repos/JunDeGuzman92/ClimateShield-Dagupan/pages -f "source[branch]=gh-pages" -f "source[path]=/"
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRANCH = "gh-pages"


def run(*cmd, cwd=None, inp=b""):
    return subprocess.run(list(cmd), check=True, cwd=cwd, input=inp,
                          capture_output=True, text=True).stdout.strip()


def branch_exists(name):
    return subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                           f"refs/heads/{name}"], capture_output=True).returncode == 0


def main():
    if not (ROOT / "field").is_dir():
        raise SystemExit("nothing to publish: field/ is missing")
    if not branch_exists(BRANCH):      # orphan branch via plumbing: never touches the main tree
        tree = run("git", "mktree", inp=b"")
        commit = run("git", "commit-tree", tree, "-m", "gh-pages root")
        run("git", "branch", BRANCH, commit)
        print("created orphan branch", BRANCH)
    tmp = Path(tempfile.mkdtemp(prefix="cs_pages_"))
    try:
        run("git", "worktree", "add", "--detach", str(tmp), BRANCH)
        run("git", "rm", "-r", "-q", "--ignore-unmatch", ".", cwd=str(tmp))   # start the branch clean
        (tmp / ".nojekyll").write_text("", encoding="utf-8")
        for f in sorted((ROOT / "field").iterdir()):
            if f.is_file():
                shutil.copy2(f, tmp / f.name)
        sha = run("git", "rev-parse", "--short", "HEAD", cwd=ROOT)
        run("git", "add", "-A", cwd=str(tmp))
        run("git", "-c", "user.name=pages publish", "-c", "user.email=noreply@github.com",
            "commit", "-m", f"Publish field pack from main {sha}", cwd=str(tmp))
        run("git", "push", "origin", BRANCH, cwd=str(tmp))
        print(f"published field/ to {BRANCH} (from main {sha})")
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(tmp)],
                       capture_output=True)


if __name__ == "__main__":
    main()
