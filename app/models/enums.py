"""Shared enumerations for roles, statuses and the D1 H-3 workflow states.
str-valued so members compare naturally with request data after validation.
"""

import enum


class UserRole(str, enum.Enum):
    """The four platform roles used by RBAC (FSR-07)."""
    GUEST = "guest"
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"


class AccountStatus(str, enum.Enum):
    """Account lifecycle: active or admin-suspended (FR-13)."""
    ACTIVE = "active"
    SUSPENDED = "suspended"


class ApprovalStatus(str, enum.Enum):
    """Admin review outcome for listings and seller applications."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ListingCondition(str, enum.Enum):
    """First-hand vs pre-owned (drives the authentication workflow)."""
    NEW = "new"
    PRE_OWNED = "pre_owned"


class WorkflowStatus(str, enum.Enum):
    """D1 H-3 item/order workflow states (see workflow_service)."""
    AVAILABLE = "available"
    COMMITTED = "committed"
    AWAITING_SHIPMENT = "awaiting_shipment"
    SHIPPED = "shipped"
    UNDER_AUTHENTICATION = "under_authentication"
    AUTHENTICATED = "authenticated"
    REJECTED = "rejected"
    SOLD = "sold"


class PaymentStatus(str, enum.Enum):
    """Simulated payment states (D1 §9.3.4) — server-controlled only."""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class DisputeStatus(str, enum.Enum):
    """Dispute lifecycle: open/under_review → resolved/dismissed."""
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AuthenticationResult(str, enum.Enum):
    """In-house authentication verdict (D1 §9.3.5)."""
    PENDING = "pending"
    AUTHENTIC = "authentic"
    COUNTERFEIT = "counterfeit"
