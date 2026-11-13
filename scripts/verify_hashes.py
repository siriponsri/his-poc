"""Verify release file integrity, excluding the hash manifest itself."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'SHA256SUMS.json').read_text())
for name,expected in manifest.items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
print(f'PASS {len(manifest)} release file hashes')
