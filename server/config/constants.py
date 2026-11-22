"""
Application Constants and Enumerations.
"""

from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class DocumentCategory(str, Enum):
    COMMERCIAL_INVOICE = "Commercial Invoice"
    PACKING_LIST = "Packing List"
    PURCHASE_ORDER = "Purchase Order"
    SHIPPING_BILL = "Shipping Bill"
    CERTIFICATE_OF_ORIGIN = "Certificate of Origin"


class ComplianceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT APPLICABLE"
