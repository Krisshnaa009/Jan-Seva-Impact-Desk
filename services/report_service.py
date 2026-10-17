"""
Financial calculation and reporting logic.
Uses Python Decimal for all monetary arithmetic — never uses float.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List

from models.expense import ExpenseRecord, ExpenseStatus


@dataclass
class ReportSummary:
    """Aggregated metrics calculated from a list of expense records."""

    total_records: int
    approved_count: int
    pending_count: int
    needs_correction_count: int
    rejected_count: int
    total_approved_amount: Decimal
    currency: str

    @property
    def total_approved_display(self) -> str:
        return f"{self.currency} {self.total_approved_amount:,.2f}"


def calculate_summary(records: List[ExpenseRecord]) -> ReportSummary:
    """
    Compute summary metrics from a list of expense records.
    Only APPROVED records with a valid positive amount contribute to the monetary total.
    """
    approved = [r for r in records if r.status == ExpenseStatus.APPROVED]
    pending = [r for r in records if r.status == ExpenseStatus.PENDING]
    needs_correction = [r for r in records if r.status == ExpenseStatus.NEEDS_CORRECTION]
    rejected = [r for r in records if r.status == ExpenseStatus.REJECTED]

    # Sum only approved records with a valid positive amount
    approved_total = Decimal("0")
    for rec in approved:
        v = rec.amount_value
        if v is not None and v > Decimal("0"):
            approved_total += v

    # Determine primary currency (most common among approved records)
    currencies = [r.currency for r in approved if r.currency]
    currency = max(set(currencies), key=currencies.count) if currencies else "INR"

    return ReportSummary(
        total_records=len(records),
        approved_count=len(approved),
        pending_count=len(pending),
        needs_correction_count=len(needs_correction),
        rejected_count=len(rejected),
        total_approved_amount=approved_total,
        currency=currency,
    )


def get_approved_records(records: List[ExpenseRecord]) -> List[ExpenseRecord]:
    """Return only APPROVED records with a valid positive amount."""
    return [
        r
        for r in records
        if r.status == ExpenseStatus.APPROVED
        and r.amount_value is not None
        and r.amount_value > Decimal("0")
    ]


def get_unresolved_records(records: List[ExpenseRecord]) -> List[ExpenseRecord]:
    """Return records that are NOT approved and NOT rejected (still need action)."""
    return [
        r
        for r in records
        if r.status in (ExpenseStatus.PENDING, ExpenseStatus.NEEDS_CORRECTION)
    ]
