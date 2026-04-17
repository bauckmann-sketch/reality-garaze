"""ORM models for the Sreality Tracker."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Numeric,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.database import Base


class Filter(Base):
    """A saved Sreality search filter (e.g. 'Garáže Praha 4')."""

    __tablename__ = "filters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    category_type = Column(String(50), nullable=True)  # prodej/pronájem/dražby
    is_active = Column(Boolean, default=True, nullable=False)
    scrape_interval_hours = Column(Integer, default=24, nullable=False)
    last_scraped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    listings = relationship("Listing", back_populates="filter", lazy="dynamic")

    def __repr__(self):
        return f"<Filter(id={self.id}, name='{self.name}')>"


class Listing(Base):
    """A single real estate listing from Sreality."""

    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filter_id = Column(Integer, ForeignKey("filters.id"), nullable=False)

    # Sreality identifiers
    sreality_id = Column(BigInteger, nullable=False, unique=True, index=True)
    url = Column(Text, nullable=True)

    # Basic info
    name = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(12, 2), nullable=True)
    price_note = Column(Text, nullable=True)
    area_m2 = Column(Numeric(10, 2), nullable=True)
    locality = Column(String(500), nullable=True)

    # Seller
    seller_name = Column(String(255), nullable=True)
    seller_phone = Column(String(100), nullable=True)
    seller_email = Column(String(255), nullable=True)
    seller_company = Column(String(255), nullable=True)

    # Location
    gps_lat = Column(Float, nullable=True)
    gps_lon = Column(Float, nullable=True)

    # Property details
    building_type = Column(String(100), nullable=True)
    building_condition = Column(String(100), nullable=True)
    ownership = Column(String(100), nullable=True)
    category_type = Column(String(50), nullable=True)  # prodej/pronájem/dražby

    # AI analysis outputs
    ai_vat_status = Column(String(50), nullable=True)  # s_dph / bez_dph / neplatce / neuvedeno
    ai_fees = Column(String(255), nullable=True)  # amount or "včetně poplatků"
    ai_price_note_analysis = Column(Text, nullable=True)
    ai_validated_area = Column(Numeric(10, 2), nullable=True)
    ai_condition = Column(String(255), nullable=True)
    ai_raw_response = Column(Text, nullable=True)
    ai_analyzed_at = Column(DateTime, nullable=True)

    # Lifecycle tracking
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    filter = relationship("Filter", back_populates="listings")
    price_history = relationship("PriceHistory", back_populates="listing", lazy="dynamic",
                                  order_by="PriceHistory.recorded_at.desc()")

    __table_args__ = (
        Index("ix_listings_filter_active", "filter_id", "is_active"),
        Index("ix_listings_lifecycle", "first_seen", "last_seen"),
    )

    def __repr__(self):
        return f"<Listing(id={self.id}, sreality_id={self.sreality_id}, price={self.price})>"

    @property
    def price_per_m2(self) -> Decimal | None:
        """Calculate price per square meter."""
        if self.price and self.area_m2 and self.area_m2 > 0:
            return round(self.price / self.area_m2, 2)
        return None

    @property
    def days_on_market(self) -> int | None:
        """Calculate days the listing has been active."""
        if self.first_seen:
            end = self.last_seen or datetime.utcnow()
            return (end - self.first_seen).days
        return None

    @property
    def sreality_url(self) -> str:
        """Generate the Sreality detail URL."""
        return f"https://www.sreality.cz/detail/{self.sreality_id}"


class PriceHistory(Base):
    """Price change record for a listing."""

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    price_per_m2 = Column(Numeric(10, 2), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    listing = relationship("Listing", back_populates="price_history")

    __table_args__ = (
        Index("ix_price_history_listing_time", "listing_id", "recorded_at"),
    )

    def __repr__(self):
        return f"<PriceHistory(listing_id={self.listing_id}, price={self.price}, at={self.recorded_at})>"
