from typing import Any
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @classmethod
    def __declare_last__(cls):
        pass
