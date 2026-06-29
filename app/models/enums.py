import enum


class UserRole(str, enum.Enum):
    GUEST = "guest"
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"


class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ListingCondition(str, enum.Enum):
    NEW = "new"
    PRE_OWNED = "pre_owned"


class WorkflowStatus(str, enum.Enum):
    AVAILABLE = "available"
    COMMITTED = "committed"
    AWAITING_SHIPMENT = "awaiting_shipment"
    SHIPPED = "shipped"
    UNDER_AUTHENTICATION = "under_authentication"
    AUTHENTICATED = "authenticated"
    REJECTED = "rejected"
    SOLD = "sold"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class DisputeStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AuthenticationResult(str, enum.Enum):
    PENDING = "pending"
    AUTHENTIC = "authentic"
    COUNTERFEIT = "counterfeit"
