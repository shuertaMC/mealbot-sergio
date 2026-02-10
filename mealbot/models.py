from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    name = Column(String, primary_key=True)
    admin = Column(String, nullable=False)
    cross_match_trait = Column(String, nullable=True)


class Member(Base):
    __tablename__ = "members"

    organization = Column(String, ForeignKey("organizations.name"), primary_key=True)
    email = Column(String, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)
    pair_counts = Column(JSONB, nullable=False)
    active = Column(Boolean, nullable=False)


class Round(Base):
    __tablename__ = "rounds"

    organization = Column(String, ForeignKey("organizations.name"), primary_key=True)
    id = Column(Integer, primary_key=True, nullable=False)
    scheduled_date = Column(DateTime, nullable=False)
    done = Column(Boolean, nullable=False)


class Pair(Base):
    __tablename__ = "pairs"

    organization = Column(String, ForeignKey("organizations.name"), primary_key=True)
    id1 = Column(String, primary_key=True, nullable=False)
    id2 = Column(String, primary_key=True, nullable=False)
    extraid = Column("extraid", String, primary_key=True, nullable=True)
    round = Column(Integer, primary_key=True, nullable=False)
