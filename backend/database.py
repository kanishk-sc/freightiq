from sqlmodel import Session, SQLModel, create_engine

from models import AuditFlag, Invoice, LineItem  # noqa: F401

DATABASE_URL = "sqlite:///./freightiq.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
