import datetime
from typing import Optional, Dict, Any
import jwt
import bcrypt
from sqlalchemy.orm import Session
from ..models.user import User
from ..models.workspace import Workspace
from ..config import settings


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[datetime.timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
        else:
            expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.AUTH_SECRET, algorithm="HS256")
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, settings.AUTH_SECRET, algorithms=["HS256"])
            return payload
        except jwt.PyJWTError:
            return None

    @classmethod
    def register_user(cls, db: Session, email: str, password: str) -> User:
        existing = db.query(User).filter(User.email == email.lower().strip()).first()
        if existing:
            raise ValueError(f"User with email '{email}' already exists.")

        user = User(
            email=email.lower().strip(),
            hashed_password=cls.hash_password(password),
            auth_subject=email.lower().strip(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create a default personal workspace for every new user
        default_ws = Workspace(
            owner_id=user.id,
            name="Default Workspace",
        )
        db.add(default_ws)
        db.commit()

        return user

    @classmethod
    def authenticate_user(cls, db: Session, email: str, password: str) -> Optional[User]:
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if not user:
            return None
        if not cls.verify_password(password, user.hashed_password):
            return None
        return user
