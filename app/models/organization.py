"""SQLAlchemy ORM model for the organizations table."""

from sqlalchemy import CheckConstraint, Column, String

from app.database import Base


class Organization(Base):
    """
    Organization model representing the organizations table.

    Organizations are the top-level entities in Mealbot. Each organization
    has an admin and can optionally have a cross_match_trait for pairing logic.
    """

    __tablename__ = "organizations"

    # name is the primary key (VARCHAR)
    name = Column(String, primary_key=True, nullable=False)

    # admin is required and must have length > 0
    admin = Column(String, nullable=False)

    # cross_match_trait is optional
    cross_match_trait = Column(String, nullable=True)

    # Add CHECK constraint for admin (length > 0)
    __table_args__ = (CheckConstraint("length(admin) > 0", name="organizations_admin_check"),)

    def __repr__(self) -> str:
        return f"<Organization(name={self.name}, admin={self.admin})>"
