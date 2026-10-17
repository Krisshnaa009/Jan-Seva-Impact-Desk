"""
Pydantic data models for expense records in JanSeva Impact Desk.
"""
from __future__ import annotations

import uuid
from datetime import date as date_type
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class ExpenseStatus(str, Enum):
    """Review lifecycle status for an expense record."""

    PENDING = "Pending Review"
    NEEDS_CORRECTION = "Needs Correction"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class ExpenseCategory(str, Enum):
    """Standard NGO expense categories."""

    FOOD = "Food & Nutrition"
    MEDICAL = "Medical & Health"
    EDUCATION = "Education & Training"
    TRANSPORT = "Transport & Logistics"
    SUPPLIES = "Supplies & Materials"
    UTILITIES = "Utilities"
    SALARIES = "Salaries & Wages"
    RENT = "Rent & Accommodation"
    COMMUNICATION = "Communication"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class ValidationIssue(BaseModel):
    """A single validation issue found on a record."""

    field: str
    message: str
    severity: str = "warning"  # "warning" | "error"


def _parse_date(v: Any) -> Optional[date_type]:
    """Coerce a value to a Python date, returning None if not parseable."""
    if v is None or v == "" or v == "unknown":
        return None
    if isinstance(v, date_type):
        return v
    from datetime import datetime  # noqa: PLC0415
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(v), fmt).date()
        except ValueError:
            continue
    return None  # Unparseable — validation service will flag it


def _parse_amount(v: Any) -> Optional[Decimal]:
    """Coerce a value to Decimal, returning None if not parseable."""
    if v is None or v == "" or v == "unknown":
        return None
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        return None


class ExpenseRecord(BaseModel):
    """
    A single expense record extracted from a receipt image.
    All monetary values are stored as Decimal for precision.

    Note: `date` and `amount` are stored as Any internally so that
    Pydantic v2 validators can return None freely. Use the typed
    properties `date_value` and `amount_value` for type-safe access.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_filename: str = ""
    # Stored as Any to allow free coercion including None returns
    date: Any = None
    vendor: str = ""
    amount: Any = None
    currency: str = "INR"
    description: str = ""
    category: ExpenseCategory = ExpenseCategory.UNKNOWN
    receipt_number: str = ""
    status: ExpenseStatus = ExpenseStatus.PENDING
    validation_issues: List[ValidationIssue] = Field(default_factory=list)
    extraction_mode: str = "mock"  # "ai" | "mock" | "manual"
    notes: str = ""

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("date", mode="before")
    @classmethod
    def coerce_date(cls, v: Any) -> Optional[date_type]:
        return _parse_date(v)

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, v: Any) -> Optional[Decimal]:
        return _parse_amount(v)

    @field_validator("category", mode="before")
    @classmethod
    def coerce_category(cls, v: Any) -> ExpenseCategory:
        if v is None or v == "":
            return ExpenseCategory.UNKNOWN
        if isinstance(v, ExpenseCategory):
            return v
        for cat in ExpenseCategory:
            if cat.value.lower() == str(v).lower() or cat.name.lower() == str(v).lower():
                return cat
        return ExpenseCategory.UNKNOWN

    # ------------------------------------------------------------------ #
    # Typed property accessors
    # ------------------------------------------------------------------ #

    @property
    def date_value(self) -> Optional[date_type]:
        if isinstance(self.date, date_type):
            return self.date
        return _parse_date(self.date)

    @property
    def amount_value(self) -> Optional[Decimal]:
        if isinstance(self.amount, Decimal):
            return self.amount
        return _parse_amount(self.amount)

    # ------------------------------------------------------------------ #
    # Convenience display helpers
    # ------------------------------------------------------------------ #

    @property
    def amount_display(self) -> str:
        v = self.amount_value
        if v is None:
            return "—"
        return f"{self.currency} {v:,.2f}"

    @property
    def date_display(self) -> str:
        v = self.date_value
        if v is None:
            return "—"
        return v.strftime("%d %b %Y")

    @property
    def is_approved(self) -> bool:
        return self.status == ExpenseStatus.APPROVED

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.validation_issues)

    @property
    def category_value(self) -> str:
        if hasattr(self.category, "value"):
            return str(self.category.value)
        return str(self.category) if self.category else "Unknown"

    @property
    def status_value(self) -> str:
        if hasattr(self.status, "value"):
            return str(self.status.value)
        return str(self.status) if self.status else "Pending Review"

    def clear_issues(self) -> None:
        self.validation_issues = []

    def add_issue(self, field: str, message: str, severity: str = "warning") -> None:
        self.validation_issues.append(
            ValidationIssue(field=field, message=message, severity=severity)
        )

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for display in a DataFrame."""
        return {
            "ID": self.id[:8],
            "Date": self.date_display,
            "Vendor": self.vendor or "—",
            "Description": self.description or "—",
            "Category": self.category_value,
            "Amount": self.amount_display,
            "Receipt #": self.receipt_number or "—",
            "Status": self.status_value,
            "Source": self.source_filename,
            "Mode": self.extraction_mode,
        }
