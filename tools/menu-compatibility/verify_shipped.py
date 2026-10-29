"""Refuse publication unless the approved exact pack-owned derivative is present."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pack', type=Path, required=True)
args = parser.parse_args()
profile = json.loads((Path(__file__).parent / 'patch-provenance.json').read_text(encoding='utf-8'))
outer = (args.pack / 'mods' / profile['candidateOuter']['path']).read_bytes()
def verify(data, row):
    if len(data) != row['sizeBytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
        raise ValueError('Pack-owned menu derivative differs from its approved size/SHA256')
verify(outer, profile['candidateOuter'])
with zipfile.ZipFile(io.BytesIO(outer)) as archive:
    nested = archive.read(profile['candidateNested']['path'])
verify(nested, profile['candidateNested'])
with zipfile.ZipFile(io.BytesIO(nested)) as archive:
    target = archive.read(profile['caller']['class'] + '.class')
if hashlib.sha256(target).hexdigest() != profile['classProof']['preparedClassSha256']:
    raise ValueError('Prepared MenuRegistry class differs from the approved reference')
print(json.dumps({'status': 'PASS', 'kind': 'exact pack-owned menu derivative',
                  'outerSha256': profile['candidateOuter']['sha256'], 'guardedCallSites': 1,
                  'nativeClientOrEventRunClaimed': False}, sort_keys=True))
