import os, sys, shutil, subprocess, time, json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from push_autopatch import update_manifest, SCRIPT_DIR

cfg = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'github_token.json')))
tok = cfg.get('github_token', '').strip()
repo_owner = cfg.get('repo_owner', 'rscomputer204-netizen').strip()
repo_name = cfg.get('autopatch_repo_name', 'R1_AutoPatch_Database').strip()
branch = cfg.get('autopatch_branch', 'main').strip()

manifest = update_manifest()
print(f"Deploying {len(manifest)} patches to https://github.com/{repo_owner}/{repo_name} [{branch}]...")

import tempfile
temp_dir = tempfile.mkdtemp(prefix='test_push_')
try:
    for item in os.listdir(SCRIPT_DIR):
        if item.startswith('.') or item == '__pycache__' or item.endswith('.pyc') or item == 'deploy_cli.py':
            continue
        s = os.path.join(SCRIPT_DIR, item)
        d = os.path.join(temp_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(s, d)

    readme = os.path.join(temp_dir, 'README.md')
    with open(readme, 'w', encoding='utf-8') as f:
        f.write(f'# R1 AutoPatch Database 🚀\nCloud repository of BIOS fix and patch scripts for **R1 BIOS TOOL**.\n\nTotal Patches: {len(manifest)}\n')

    subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'R1 LAB'], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'r1lab@bios-tool.local'], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(['git', 'checkout', '-b', branch], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(['git', 'add', '.'], cwd=temp_dir, check=True, capture_output=True)

    commit_msg = f'AutoPatch Cloud Sync: {len(manifest)} patches loaded ({time.strftime("%Y-%m-%d %H:%M")})'
    subprocess.run(['git', 'commit', '-m', commit_msg], cwd=temp_dir, check=True, capture_output=True)

    auth_url = f'https://x-access-token:{tok}@github.com/{repo_owner}/{repo_name}.git'
    res = subprocess.run(
        f'git -c credential.helper= push -u "{auth_url}" {branch} --force',
        shell=True, capture_output=True, text=True, cwd=temp_dir
    )
    print('Return code:', res.returncode)
    print('Stdout:\n', res.stdout)
    print('Stderr:\n', res.stderr)
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
