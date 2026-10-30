"""Verify the selected author files without rewriting any game JAR."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=Path('.'))
    args = parser.parse_args()
    root = args.pack.resolve()
    lock = json.loads((root/'tools/upstream/current.json').read_text(encoding='utf8'))
    expected = {}
    for row in lock['files']:
        relative = PurePosixPath(row['path'])
        assert not relative.is_absolute() and '..' not in relative.parts and ':' not in row['path']
        file = root/relative
        assert not file.is_symlink() and file.resolve().is_relative_to(root)
        assert file.stat().st_size == row['sizeBytes'], row['path']
        with file.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        assert digest == row['sha256'], row['path']
        assert row['path'] not in expected
        expected[row['path']] = digest
    actual_jars = {file.relative_to(root).as_posix() for file in (root/'mods').glob('*.jar')}
    assert actual_jars == {path for path in expected if path.startswith('mods/')}, 'Unknown or missing game JAR'
    runtime = json.loads((root/'portable-pack.json').read_text(encoding='utf-8-sig'))
    assert runtime['minecraftVersion'] == lock['minecraftVersion']
    assert runtime['loader'] == lock['loader']
    print(json.dumps({'status': 'PASS', 'authorVersion': lock['authorVersion'],
                      'authorFiles': len(expected), 'jarCount': len(actual_jars),
                      'gameJarsRewritten': False, 'runtimeVerified': False}))

if __name__ == '__main__':
    main()
