from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from data_types import SignupRequest, LoginRequest, Token, ProfileResponse, ProfileUpdateRequest
from db import SessionLocal, User
from sqlalchemy.exc import SQLAlchemyError
from jwt_auth import create_access_token, get_current_user
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordRequestForm


password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummy_password")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return password_hash.hash(password)

def get_user(db, email: str):
    return db.scalar(select(User).where(User.email == email))

def authenticate_user(db, identifier: str, password: str):
    user = get_user(db, identifier)
    if user is None:
        verify_password(password, DUMMY_HASH)
        return None
    if not verify_password(password, user.password):
        return None
    return user

@app.get("/")
def root():
    return {"message": "API is running"}

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with SessionLocal() as db:
        user = authenticate_user(db, form_data.username, form_data.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = create_access_token(data={"sub": str(user.id_user)})
        return Token(
            access_token=access_token,
            token_type="bearer"
        )

        
@app.post("/signup", status_code=201)
def signup(data: SignupRequest):
    with SessionLocal() as db:
        try:
            email_exists = db.scalar(select(User).where(User.email == data.email))
            if email_exists:
                raise HTTPException(status_code=400, detail="Email already used")
            username_exists = db.scalar(select(User).where(User.username == data.username))
            if username_exists:
                raise HTTPException(status_code=400, detail="Username already used")
            user = User(
                name=data.name,
                firstname=data.firstname,
                username=data.username,
                email=data.email,
                password=get_password_hash(data.password)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return {
                "message": "Account successfully created",
                "id": user.id_user
            }
        except HTTPException:
            raise
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(status_code=500, detail="Database error")

@app.get("/home")
def home(current_user: User = Depends(get_current_user)):
    return {"message": f"Welcome {current_user.firstname}"}

@app.get("/account", response_model=ProfileResponse)
def get_account(current_user: User = Depends(get_current_user)):
    return current_user

@app.patch("/account", response_model=ProfileResponse)
def update_account(data: ProfileUpdateRequest, current_user: User = Depends(get_current_user)):
    with SessionLocal() as db:
        try:
            user = db.scalar(select(User).where(User.id_user == current_user.id_user))
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            if data.email != user.email:
                email_exists = db.scalar(select(User).where(User.email == data.email, User.id_user != user.id_user))
                if email_exists:
                    raise HTTPException(status_code=400, detail="Email already used")
            user.name = data.name
            user.firstname = data.firstname
            user.email = data.email
            user.phone = data.phone
            db.commit()
            db.refresh(user)
            return user
        except HTTPException:
            raise
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(status_code=500, detail="Database error")

@app.delete("/account", status_code=200)
def delete_account(current_user: User = Depends(get_current_user)):
    with SessionLocal() as db:
        try:
            user = db.scalar(select(User).where(User.id_user == current_user.id_user))
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            db.delete(user)
            db.commit()
            return {"message": "Account successfully deleted"}
        except HTTPException:
            raise
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Account could not be deleted because it still has related data")
