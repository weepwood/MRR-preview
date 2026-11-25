"""Track only the two public integration branches; never publish main."""
import json
import os
import re
import subprocess
import urllib.request

SOURCE = 'https://github.com/weepwood/MRR.git'
ROOT = 'https://weepwood.github.io/MRR-preview/'
BRANCHES = {'v1.1': 'integration/v1.1', 'v1.2': 'integration/v1.2'}

def main():
    raw = subprocess.check_output(['git', 'ls-remote', SOURCE, *['refs/heads/' + b for b in BRANCHES.values()]], text=True, timeout=30)
    refs = dict((ref, sha) for sha, ref in (line.split() for line in raw.splitlines()))
    matrix = []
    for version, branch in BRANCHES.items():
        sha = refs.get('refs/heads/' + branch, '')
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise ValueError(f'missing exact source ref: {branch}')
        matrix.append({'version': version, 'branch': branch, 'sha': sha})
    try:
        with urllib.request.urlopen(ROOT + 'versions.json?run=' + os.environ.get('GITHUB_RUN_ID', 'local'), timeout=15) as response:
            published = json.load(response)['versions']
        changed = published != matrix
    except (OSError, KeyError, ValueError):
        changed = True
    changed = changed or os.getenv('FORCE_BUILD', '').lower() == 'true'
    print(json.dumps(matrix, indent=2))
    with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
        out.write('matrix=' + json.dumps({'include': matrix}, separators=(',', ':')) + '\n')
        out.write('changed=' + str(changed).lower() + '\n')

if __name__ == '__main__':
    main()
