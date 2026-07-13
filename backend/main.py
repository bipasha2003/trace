from fastapi import FastAPI
from schema import CategoryCreateSchema, UserCreateSchema

app = FastAPI()

@app.get("/")
async def index():
    return {"status": 200, "Text": "Welcome to my app"}

@app.get("/user")
async def get_user():
    return {"id": 1, "first_name": "Bipasha", "last_name": "Bagchi", "age": 22}

@app.get("/products")
async def get_product():
    return {"id": 1, "name": "iphone 17 pro max", "brand": "apple", "colour": "Red"}

@app.get("/categories")
async def get_categories(q: str | None = None):
    return [
        {"id": 1, "name": "Phone"},
        {"id": 2, "name": "Laptop"},
    ]

@app.get("/categories/{id}")
async def get_category(id: int):
    return {"id": id, "name": "Phone"}

@app.post("/categories")
async def create_category(data: CategoryCreateSchema):
    return data

@app.post("/users")
async def create_user(data: UserCreateSchema):
    return data

@app.get("/users/{user_id}")
async def get_user_detail(user_id: int):
    return {
        "id": user_id,
        "name": "Bipasha",
        "email": "bipasha@example.com",
        "addresses": [
            {"id": 1, "street": "123 Main St", "city": "Metropolis", "user_id": user_id}
        ],
    }

from schema import CategoryCreateSchema, UserCreateSchema

app = FastAPI()

@app.get("/")
async def index():
    return {"status": 200, "Text": "Welcome to my app"}

@app.get("/user")
async def get_user():
    return {"id": 1, "first_name": "Bipasha", "last_name": "Bagchi", "age": 22}

@app.get("/products")
async def get_product():
    return {"id": 1, "name": "iphone 17 pro max", "brand": "apple", "colour": "Red"}

@app.get("/categories")
async def get_categories(q: str | None = None):
    return [
        {"id": 1, "name": "Phone"},
        {"id": 2, "name": "Laptop"},
    ]

@app.get("/categories/{id}")
async def get_category(id: int):
    return {"id": 1, "name": "Phone"}

@app.post("/categories")
async def create_category(data: CategoryCreateSchema):
    return data

@app.post("/users")
async def create_user(data: UserCreateSchema):
    return data

@app.get("/users")
async def get_user_detail():
    return {
        "id": 1,
        "name": "Bipasha",
        "email": "bipasha@example.com",
        "addresses": [
            {"id": 1, "street": "123 Main St", "city": "Metropolis", "user_id": 1}
        ],
    }
