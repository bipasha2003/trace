from pydantic import BaseModel

class CategoryCreateSchema(BaseModel):
    id : int 
    name : str
    description : str | None = None

class AddressSchema(BaseModel):
    id: int
    street: str
    city: str
    user_id: int

class UserCreateSchema(BaseModel):
    id: int
    name: str
    email: str | None = None
    addresses: list[AddressSchema] | None = None
