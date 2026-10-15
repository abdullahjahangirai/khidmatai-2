from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum, ForeignKey, Text, Float, ARRAY
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .models import Base, Branch, Organization, Profile, ServiceCategoryEnum, ServiceCategoryEnum as SCEnum

# ------------------------------------------------------------
# Contact model for multiple branch contacts
# ------------------------------------------------------------
class ContactTypeEnum(str, enum.Enum):
    phone = "phone"
    whatsapp = "whatsapp"
    email = "email"

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    type = Column(SAEnum(ContactTypeEnum), nullable=False)
    value = Column(String, nullable=False)
    label = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)
    branch = relationship("Branch", back_populates="contacts")

# Extend Branch with contacts relationship
Branch.contacts = relationship(
    "Contact",
    back_populates="branch",
    cascade="all, delete-orphan",
)

# ------------------------------------------------------------
# Donor profile
# ------------------------------------------------------------
class DonorProfile(Base):
    __tablename__ = "donor_profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, unique=True)
    donor_type = Column(String, nullable=False)  # "individual" or "corporate"
    preferred_categories = Column(ARRAY(SAEnum(ServiceCategoryEnum)), nullable=True)
    preferred_city = Column(String, nullable=True)
    budget_range = Column(String, nullable=True)
    contact_pref = Column(String, nullable=True)
    verification_status = Column(String, default="pending")
    profile = relationship("Profile", backref="donor_profile")

# ------------------------------------------------------------
# Funding needs
# ------------------------------------------------------------
class FundingNeedStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    funded = "funded"
    expired = "expired"

class FundingNeed(Base):
    __tablename__ = "funding_needs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(SAEnum(ServiceCategoryEnum), nullable=False)
    target_amount = Column(Float, nullable=False)
    amount_raised = Column(Float, default=0.0)
    status = Column(SAEnum(FundingNeedStatusEnum), default=FundingNeedStatusEnum.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    organization = relationship("Organization", back_populates="funding_needs")
    branch = relationship("Branch", back_populates="funding_needs")

# Extend Organization with funding_needs relationship
Organization.funding_needs = relationship(
    "FundingNeed",
    back_populates="organization",
    cascade="all, delete-orphan",
)

# Extend Branch with funding_needs relationship
Branch.funding_needs = relationship(
    "FundingNeed",
    back_populates="branch",
    cascade="all, delete-orphan",
)

# ------------------------------------------------------------
# Donations
# ------------------------------------------------------------
class DonationStatusEnum(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    refunded = "refunded"

class Donation(Base):
    __tablename__ = "donations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    donor_profile_id = Column(UUID(as_uuid=True), ForeignKey("donor_profiles.id"), nullable=False)
    need_id = Column(UUID(as_uuid=True), ForeignKey("funding_needs.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(SAEnum(DonationStatusEnum), default=DonationStatusEnum.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    donor_profile = relationship("DonorProfile", backref="donations")
    need = relationship("FundingNeed", backref="donations")
