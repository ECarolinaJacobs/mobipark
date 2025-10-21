from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from importlib import import_module
from typing import Dict, Type
import secrets

app = FastAPI()

# ----------------------------
# ✅ In-memory data storage
# ----------------------------
db: Dict[str, Dict[int, dict]] = {
    "users": {},
    "products": {},
    "orders": {}
}

SESSIONS: Dict[str, dict] = {}  # token → user info


# ----------------------------
# ✅ Auth Models
# ----------------------------
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    full_name: str
    password: str


# ----------------------------
# ✅ Auth Endpoints
# ----------------------------
@app.post("/register")
def register_user(data: RegisterRequest):
    # Check if username exists
    for user in db["users"].values():
        if user["username"] == data.username:
            raise HTTPException(status_code=400, detail="Username already exists")

    new_id = len(db["users"]) + 1
    new_user = data.dict()
    new_user["role"] = "user"
    new_user["owner"] = data.username
    db["users"][new_id] = new_user
    return {"message": "User registered successfully", "id": new_id}


@app.post("/login")
def login_user(credentials: LoginRequest):
    # Verify username and password
    user = next((u for u in db["users"].values() if u["username"] == credentials.username), None)
    if not user or user["password"] != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Generate session token
    token = secrets.token_hex(16)
    SESSIONS[token] = {"username": user["username"], "role": user["role"]}
    return {"message": "Login successful", "token": token, "role": user["role"]}


# ----------------------------
# ✅ Middleware: Verify Token
# ----------------------------
@app.middleware("http")
async def verify_session_token(request: Request, call_next):
    # Skip login/register endpoints
    if request.url.path in ["/login", "/register"]:
        return await call_next(request)

    token = request.headers.get("X-Session-Token")
    user_data = SESSIONS.get(token)

    if not user_data:
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden: Invalid or missing session token"},
        )

    request.state.user = user_data
    return await call_next(request)


# ----------------------------
# ✅ CRUD Factory
# ----------------------------
def create_crud_routes(resource: str, model_cls: Type[BaseModel]):
    db[resource] = db.get(resource, {})

    @app.get(f"/{resource}")
    def get_all(request: Request):
        user = request.state.user
        items = list(db[resource].values())
        if user["role"] != "admin":
            items = [i for i in items if i.get("owner") == user["username"]]
        return items

    @app.get(f"/{resource}/{{item_id}}")
    def get_one(request: Request, item_id: int):
        user = request.state.user
        item = db[resource].get(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"{resource[:-1].title()} not found")
        if user["role"] != "admin" and item.get("owner") != user["username"]:
            raise HTTPException(status_code=403, detail="Forbidden: Access denied")
        return item

    @app.post(f"/{resource}")
    def create_item(request: Request, item: model_cls):
        user = request.state.user
        if user["role"] == "user" and resource not in ["orders"]:
            raise HTTPException(status_code=403, detail="Forbidden: Users cannot create this resource")

        new_id = len(db[resource]) + 1
        db[resource][new_id] = {**item.dict(), "owner": user["username"]}
        return {"id": new_id, **db[resource][new_id]}

    @app.put(f"/{resource}/{{item_id}}")
    def update_item(request: Request, item_id: int, item: model_cls):
        user = request.state.user
        existing = db[resource].get(item_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"{resource[:-1].title()} not found")
        if user["role"] != "admin" and existing.get("owner") != user["username"]:
            raise HTTPException(status_code=403, detail="Forbidden: You cannot modify this item")
        db[resource][item_id] = {**item.dict(), "owner": existing["owner"]}
        return {"id": item_id, **db[resource][item_id]}

    @app.delete(f"/{resource}/{{item_id}}")
    def delete_item(request: Request, item_id: int):
        user = request.state.user
        existing = db[resource].get(item_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"{resource[:-1].title()} not found")
        if user["role"] != "admin" and existing.get("owner") != user["username"]:
            raise HTTPException(status_code=403, detail="Forbidden: You cannot delete this item")
        deleted = db[resource].pop(item_id)
        return {"deleted": deleted}


# ----------------------------
# ✅ Dynamic Model Import
# ----------------------------
def register_models():
    resources = ["users", "products", "orders"]
    for resource in resources:
        try:
            module = import_module(f"models.{resource}")
            model_cls = next(
                cls for name, cls in module.__dict__.items()
                if isinstance(cls, type) and issubclass(cls, BaseModel) and cls != BaseModel
            )
            create_crud_routes(resource, model_cls)
            print(f"✅ Registered routes for /{resource} using {model_cls.__name__}")
        except Exception as e:
            print(f"⚠️ Could not import model for {resource}: {e}")

register_models()
