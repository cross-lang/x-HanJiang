from pydantic import BaseModel


class UpdateMeRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    gender: str | None = None
    birthday: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    code: str = ""