"""Bounded tracked-text scan; prints paths only, never secret contents."""
import re
import subprocess
from pathlib import Path
patterns = [rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', rb'AKIA[0-9A-Z]{16}', rb'gh[pousr]_[A-Za-z0-9]{30,}', rb'sk-proj-[A-Za-z0-9_-]{30,}']
findings = []
for name in subprocess.check_output(['git','ls-files','-z']).split(b'\0'):
    if not name: continue
    path = Path(name.decode())
    if not path.is_file(): continue
    if path.suffix in {'.png','.jpg','.jpeg','.pdf','.mp4'}: continue
    content = path.read_bytes()
    if any(re.search(pattern,content) for pattern in patterns): findings.append(str(path))
if findings: raise SystemExit('Secret-pattern matches in: '+', '.join(findings))
print('PASS: tracked text secret-pattern scan (not a guarantee of absence)')
