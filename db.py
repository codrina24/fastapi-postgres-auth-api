import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, String, Text, text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from datetime import date, datetime


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from .env")

engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)


def db_connection(): #test db

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("✅ Connection successful!")
    except Exception as e:
        print(f"Error connection failed details: {e}")
        return False

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id_user: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    firstname: Mapped[str] =  mapped_column(String(30), nullable=False)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    email: Mapped[str] =  mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)


class Event(Base):
    __tablename__ = "events"
    id_event: Mapped[int] = mapped_column(primary_key=True)
    id_user: Mapped[int] = mapped_column(ForeignKey("users.id_user"), index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    event_date: Mapped[date] = mapped_column()
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

class Guest(Base):
    __tablename__ = "guests"
    id_guest: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id_event"))
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(255),nullable=True)
    relation: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    invitation_token: Mapped[str] = mapped_column(String(64), unique=True)

class RSVP(Base):
    __tablename__ = "rsvp"
    id_rsvp: Mapped[int] = mapped_column(primary_key=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id_guest"))
    attending: Mapped[bool] = mapped_column()
    guests_count: Mapped[int] = mapped_column(default=1)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    responded_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


def db_setup():
    Base.metadata.create_all(engine)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

