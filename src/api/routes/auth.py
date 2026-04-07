from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import jwt
from src.utils.auth_utils import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str

@router.post("/register")
def register(user: UserCreate):
    """Registers a new user and securely hashes their password."""
    # Import here to avoid circular import issues
    from src.db.models import User
    from src.db.database import SessionLocal

    db = SessionLocal()
    try:
        # Check if user exists
        existing = db.query(User).filter(User.username == user.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already registered")

        # Create and commit new user
        db_user = User(
            username=user.username,
            full_name=user.full_name,
            hashed_password=get_password_hash(user.password),
            role="Intelligence Officer"
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return {"message": "User created successfully"}
    finally:
        db.close()

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Verifies credentials and issues a JWT token."""
    from src.db.models import User
    from src.db.database import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")

        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    finally:
        db.close()

@router.get("/me")
def get_me(token: str = Depends(oauth2_scheme)):
    """Reads the token to tell the frontend who is currently logged in."""
    from src.db.models import User
    from src.db.database import SessionLocal

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.username == username).first()
            if not db_user:
                raise HTTPException(status_code=401, detail="User not found")
            return {"username": db_user.username, "name": db_user.full_name, "role": db_user.role, "initials": db_user.full_name[:2].upper()}
        finally:
            db.close()
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")