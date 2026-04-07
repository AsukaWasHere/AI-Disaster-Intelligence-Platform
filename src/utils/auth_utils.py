import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Security configuration (Keep these secret in production)
SECRET_KEY = "sentinel-super-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 hours

# Sets up bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    # Convert to bytes if string, truncate to 72 bytes (bcrypt limit)
    if isinstance(password, bytes):
        password = password[:72]
    else:
        password = password.encode("utf-8")[:72]
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    # Convert to bytes if string, truncate to 72 bytes (bcrypt limit)
    if isinstance(plain_password, bytes):
        plain_password = plain_password[:72]
    else:
        plain_password = plain_password.encode("utf-8")[:72]
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """Generates a temporary digital passport (token) for the user."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)