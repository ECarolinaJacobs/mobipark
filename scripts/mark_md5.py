import json
from pathlib import Path

USERS_FILE = Path("data/users.json")  

with open(USERS_FILE, "r", encoding="utf-8") as f:
    users = json.load(f)

changed = False
for u in users:
    if "hash_type" not in u:
        pw = u.get("password", "")
        if isinstance(pw, str) and (pw.startswith("$2a$") or pw.startswith("$2b$") or pw.startswith("$2y$")):
            u["hash_type"] = "bcrypt"
        else:
            u["hash_type"] = "md5"
        changed = True

if changed:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    print("Users updated with hash_type")
else:
    print("No changes needed")
