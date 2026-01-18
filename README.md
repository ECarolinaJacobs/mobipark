# FastAPI Project — Endpoints & Contribution Guide

> Clear instructions for setting up, running, adding endpoints, and contributing.

---

## Badges

![python](https://img.shields.io/badge/python-3.10%2B-blue)
![fastapi](https://img.shields.io/badge/FastAPI-%F0%9F%92%A1-brightgreen)

---

## Prerequisites

Install required packages before running the project:

```bash
pip install "fastapi[standard]"
```

> Optionally create and activate a virtual environment first (recommended):

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate     # Windows
```

---

## Running the server

Start the FastAPI development server with auto-reload:

```bash
fastapi dev main.py
```

You can then visit the interactive API docs at `http://127.0.0.1:8000/docs` (Swagger) or `http://127.0.0.1:8000/redoc`.

---

## Project folder (recommended)

```
project_root/
├─ main.py
├─ models/
│  └─ __init__.py
├─ endpoints/
│  ├─ __init__.py
│  └─ auth.py
├─ tests/
└─ README.md
```

---

## How to add an endpoint (step-by-step)

1. **Create a model**

   * Add a file under `models/`, e.g. `models/user.py`.
   * Use Pydantic models for request/response schemas:

```python
# models/user.py
from pydantic import BaseModel

class UserCreate(BaseModel):
    id: int
    name: str
    email: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
```

2. **Create an endpoint file**

   * Add a file to `endpoints/`, e.g. `endpoints/users.py`.

3. **Create router & logic**

   * Import `APIRouter` and create a `router` instance.
   * Add route handlers under `router`.

```python
# endpoints/users.py
from fastapi import APIRouter, HTTPException
from models.user import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])

# in-memory example store (replace with DB/service)
_fake_db: dict[int, UserOut] = {}

@router.post("/", response_model=UserOut)
async def create_user(payload: UserCreate):
    if payload.id in _fake_db:
        raise HTTPException(status_code=400, detail="User already exists")
    user = UserOut(**payload.dict())
    _fake_db[payload.id] = user
    return user

@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int):
    user = _fake_db.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    return user
```

4. **Register the router in `main.py`**

```python
# main.py
from fastapi import FastAPI
from endpoints.users import router as users_router

app = FastAPI()
app.include_router(users_router)
```

> See `endpoints/auth.py` for an example of how authentication routes are structured in this repo.

---

## Naming & router pattern notes

* Use `router = APIRouter()` at the top of each endpoint file.
* Prefer `prefix` (optional) and `tags` on the router for consistency.

---

## Branching rules (required)

For **each feature** or fix, create a branch following the prefixes below and a short descriptive name:

* `feature:` — new features
* `fix:` — bug fixes
* `refactor:` — refactors and cleanup

**Examples:**

```
feature:add-user-registration
fix:login_password_field_missing_hash
refactor:cleanup-auth-endpoints
```

**Git example**

```bash
# create branch
git checkout -b "feature:add-user-registration"

# push branch
git push -u origin "feature:add-user-registration"
```

---

## Pull request (PR) rules

* ❌ **Do NOT merge directly into `main`.**
* ✅ Always open a **Pull Request** to merge into `main`.
* ❌ **Do not approve or merge your own PR.** Wait for at least one other reviewer to approve.
* Include a short description, related issue (if any), and testing steps in the PR description.

---

## PR template (suggested)

```
### Summary
Short description of the change.

### Changes
- What changed
- Why it changed

### How to test
1. Step 1
2. Step 2

### Related issue
Closes #123 (or N/A)
```

---

## Checklist before creating PR

* [ ] Branch name uses one of the required prefixes
* [ ] Tests added/updated (if applicable)
* [ ] Linting passed
* [ ] Documentation updated (README or inline docs)

---

## Tips & best practices

* Keep endpoints small and focused.
* Add tests in `tests/` for non-trivial logic.
* Use environment variables for secrets and configuration.

## Database protection password -- explanation and todo:
* The production database file is encrypted with a password using SQLCipher (256-bit AES encryption).
* The password is stored in GitHub Secrets (never in code or .env files).
* When you push code, the CD pipeline automatically injects the password into the production Docker container.
* The application uses this password to unlock and access the encrypted database.
* If someone steals the database file, they cannot read it without the password.

What to do now:
* There is a .env.examples file in the code base, which also shows what needs to be added
*  USE_MOCK_DATA=true
   USE_DB_ENCRYPTION=false
   DB_PASSWORD=not-used-locally
*NOTE: the reason the password here is not-used-locally is because the database is only used at production. This means that when the pushed code goes to production, the pipeline adds the actual password which is stored in github secrets. 

*End of guide.*
