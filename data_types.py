from pydantic import BaseModel, EmailStr

class SignupRequest(BaseModel):
    name: str
    firstname: str
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ProfileResponse(BaseModel):
    name: str
    firstname: str
    username: str
    email: EmailStr
    phone: str | None = None

class ProfileUpdateRequest(BaseModel):
    name: str
    firstname: str
    email: EmailStr
    phone: str | None = None