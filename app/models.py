from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum, ForeignKey, Text, Float, ARRAY
from sqlalchemy.orm import relationship, declarative_base
import enum
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

# Enums
class RoleEnum(str, enum.Enum):
    admin = "admin"
    ngo = "ngo"
    donor = "donor"
    user = "user"

class StatusEnum(str, enum.Enum):
    active = "active"
    blocked = "blocked"

class OrgTypeEnum(str, enum.Enum):
    NGO = "NGO"
    University = "University"
    Hospital = "Hospital"

class ServiceCategoryEnum(str, enum.Enum):
    Education_IT = "Education/IT"
    Healthcare = "Healthcare"
    Welfare = "Welfare"
    Scholarship = "Scholarship"

class SubscriptionTierEnum(str, enum.Enum):
    free = "free"
    pro = "pro"

class ContactTypeEnum(str, enum.Enum):
    phone = "phone"
    whatsapp = "whatsapp"
    email = "email"

class FundingNeedStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    funded = "funded"
    expired = "expired"

class DonationStatusEnum(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    refunded = "refunded"

# Core models
class Profile(Base):
    __tablename__ = "profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(SAEnum(RoleEnum), nullable=False)
    status = Column(SAEnum(StatusEnum), default=StatusEnum.active, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(SAEnum(OrgTypeEnum), nullable=False)
    google_business_id = Column(String, nullable=True)
    subscription_tier = Column(SAEnum(SubscriptionTierEnum), default=SubscriptionTierEnum.free)
    is_verified = Column(Boolean, default=False)
    status = Column(SAEnum(StatusEnum), default=StatusEnum.active)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("Profile", backref="organizations")
    branches = relationship("Branch", back_populates="organization", cascade="all, delete-orphan")
    services = relationship("ServiceCourse", back_populates="organization", cascade="all, delete-orphan")
    ads = relationship("SponsoredAd", back_populates="organization", cascade="all, delete-orphan")
    funding_needs = relationship("FundingNeed", back_populates="organization", cascade="all, delete-orphan")

class Branch(Base):
    __tablename__ = "branches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)
    country = Column(String, nullable=True)
    province = Column(String, nullable=True)
    city = Column(String, nullable=False)
    area = Column(String, nullable=True)
    address = Column(String, nullable=False)
    postal_code = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)
    google_place_id = Column(String, nullable=True)
    google_business_location_id = Column(String, nullable=True)
    verification_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organization = relationship("Organization", back_populates="branches")
    contacts = relationship("Contact", back_populates="branch", cascade="all, delete-orphan")
    funding_needs = relationship("FundingNeed", back_populates="branch", cascade="all, delete-orphan")

class ServiceCourse(Base):
    __tablename__ = "services_courses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    title = Column(String, nullable=False)
    category = Column(SAEnum(ServiceCategoryEnum), nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    eligibility = Column(Text, nullable=True)
    cost = Column(Float, nullable=True)
    organization = relationship("Organization", back_populates="services")

class SponsoredAd(Base):
    __tablename__ = "sponsored_ads"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    title = Column(String, nullable=False)
    target_category = Column(SAEnum(ServiceCategoryEnum), nullable=False)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    organization = relationship("Organization", back_populates="ads")

# Additional models
class Contact(Base):
    __tablename__ = "contacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    type = Column(SAEnum(ContactTypeEnum), nullable=False)
    value = Column(String, nullable=False)
    label = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    branch = relationship("Branch", back_populates="contacts")

class DonorProfile(Base):
    __tablename__ = "donor_profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, unique=True)
    donor_type = Column(String, nullable=False)  # "individual" or "corporate"
    preferred_categories = Column(Text, nullable=True)  # JSON list of categories
    preferred_city = Column(String, nullable=True)
    budget_range = Column(String, nullable=True)
    contact_pref = Column(String, nullable=True)
    verification_status = Column(String, default="pending")
    profile = relationship("Profile", backref="donor_profile")

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
