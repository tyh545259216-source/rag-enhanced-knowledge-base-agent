"""扫描Git候选文件，不输出疑似秘密值；只输出文件和规则。"""
import json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
patterns={
 "windows_absolute_path":re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}"),
 "unix_user_path":re.compile(r"/(?:Users|home)/[^/\s]+"),
 "credential_assignment":re.compile(r'(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|authorization|cookie)\s*[=:]\s*[\"\'](?![<\"\'])[^\"\']{8,}[\"\']'),
 "key_like":re.compile(r"\bsk-[A-Za-z0-9_-]{16,}|\bgh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN .*PRIVATE KEY-----"),
 "jwt_like":re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}")}
names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
findings=[];large=[];count=0
for name in dict.fromkeys(names):
 if not name:continue
 p=ROOT/name
 if not p.is_file():continue
 count+=1
 if p.stat().st_size>5_000_000:large.append(name)
 try:text=p.read_text(encoding='utf-8')
 except (UnicodeDecodeError,ValueError):continue
 if name=='scripts/audit_release.py':continue # scanner自身仅规则，无真实凭证
 for rule,pattern in patterns.items():
  if pattern.search(text):findings.append({'file':name,'rule':rule})
result={'candidate_files':count,'findings':findings,'large_files_over_5MB':large,'scope':'Git candidate content, no secret values printed; .venv/logs/IDE/store/raw local evidence ignored. Heuristic scan, not a secret-free guarantee.'}
(ROOT/'docs/releases/SECURITY_SCAN.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(findings or large))
