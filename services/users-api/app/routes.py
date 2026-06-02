from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from .models import User, UserCreate

router = APIRouter(prefix="/users", tags=["users"])

# In-memory storage
_users: dict[int, dict] = {}
_next_id: int = 1


@router.post("/", response_model=User, status_code=201)
async def create_user(user: UserCreate):
    global _next_id
    now = datetime.now(timezone.utc)
    record = {
        "id": _next_id,
        "name": user.name,
        "email": user.email,
        "created_at": now,
    }
    _users[_next_id] = record
    _next_id += 1
    return User.model_validate(record)


@router.get("/", response_model=list[User])
async def list_users():
    return [User.model_validate(u) for u in _users.values()]


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int):
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    return User.model_validate(_users[user_id])


@router.put("/{user_id}", response_model=User)
async def update_user(user_id: int, user: UserCreate):
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    _users[user_id]["name"] = user.name
    _users[user_id]["email"] = user.email
    return User.model_validate(_users[user_id])


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int):
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    del _users[user_id]
