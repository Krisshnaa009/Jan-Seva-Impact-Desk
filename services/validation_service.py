"""
Validation service — pure deterministic Python logic.
Never calls an AI model. Detects missing fields, invalid values,
and possible duplicate receipts.
"""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal, InvalidOperation
from typing import List

from models.expense import ExpenseCategory, ExpenseRecord, ExpenseStatus


# --------------------------------------------------------------------------- #
# Field-level validators
# --------------------------------------------------------------------------- #

def _check_date(record: ExpenseRecord) -> None:
    v = record.date_value
    if v is None:
        record.add_issue("date", "Date is missing. Please enter the receipt date.", "error")
    elif v > date_type.today():
        record.add_issue(
            "date",
            f"Date {v} is in the future. Verify the receipt date.",
            "warning",
        )


def _check_vendor(record: ExpenseRecord) -> None:
    if not record.vendor or record.vendor.strip() == "":
        record.add_issue("vendor", "Vendor name is missing.", "error")


def _check_amount(record: ExpenseRecord) -> None:
    v = record.amount_value
    if v is None:
        record.add_issue("amount", "Amount is missing.", "error")
    else:
        try:
            amt = Decimal(str(v))
            if amt <= Decimal("0"):
                record.add_issue(
                    "amount",
                    f"Amount {amt} is not positive. Receipt amounts must be > 0.",
                    "error",
                )
            if amt > Decimal("10000000"):  # 1 crore sanity cap
                record.add_issue(
                    "amount",
                    f"Amount {amt} is unusually large. Please verify.",
                    "warning",
                )
        except (InvalidOperation, TypeError):
            record.add_issue("amount", "Amount value is invalid.", "error")


def _check_description(record: ExpenseRecord) -> None:
    if not record.description or record.description.strip() == "":
        record.add_issue(
            "description",
            "Expense description is missing. Add a brief note.",
            "warning",
        )


def _check_category(record: ExpenseRecord) -> None:
    if record.category == ExpenseCategory.UNKNOWN:
        record.add_issue(
            "category",
            "Category is unclassified. Please select the appropriate category.",
            "warning",
        )


# --------------------------------------------------------------------------- #
# Duplicate detection (cross-record)
# --------------------------------------------------------------------------- #

def _detect_duplicates(records: List[ExpenseRecord]) -> None:
    """
    Flag possible duplicates based on matching (date, vendor, amount) tuples
    or matching receipt numbers. Never labels as fraudulent.
    """
    seen_signatures: dict = {}  # signature -> first record id
    seen_receipt_numbers: dict = {}  # receipt_number -> first record id

    for rec in records:
        d = rec.date_value
        a = rec.amount_value

        # Signature-based duplicate
        if d is not None and rec.vendor and a is not None:
            sig = (d, rec.vendor.lower().strip(), a)
            if sig in seen_signatures:
                existing_id = seen_signatures[sig][:8]
                rec.add_issue(
                    "duplicate",
                    (
                        f"This receipt has the same date, vendor, and amount as "
                        f"record #{existing_id}. Please verify it is not a duplicate."
                    ),
                    "warning",
                )
            else:
                seen_signatures[sig] = rec.id

        # Receipt-number-based duplicate
        if rec.receipt_number and rec.receipt_number.strip():
            rn = rec.receipt_number.strip().lower()
            if rn in seen_receipt_numbers:
                existing_id = seen_receipt_numbers[rn][:8]
                rec.add_issue(
                    "receipt_number",
                    (
                        f"Receipt number '{rec.receipt_number}' also appears on "
                        f"record #{existing_id}. Please check for duplicates."
                    ),
                    "warning",
                )
            else:
                seen_receipt_numbers[rn] = rec.id


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def validate_record(record: ExpenseRecord) -> ExpenseRecord:
    """
    Validate a single record. Clears existing issues and runs all checks.
    Updates status to NEEDS_CORRECTION when errors are found and record is PENDING.
    """
    record.clear_issues()
    _check_date(record)
    _check_vendor(record)
    _check_amount(record)
    _check_description(record)
    _check_category(record)

    # Only auto-downgrade PENDING records; leave APPROVED/REJECTED untouched
    if record.has_errors and record.status == ExpenseStatus.PENDING:
        record.status = ExpenseStatus.NEEDS_CORRECTION

    return record


def validate_all(records: List[ExpenseRecord]) -> List[ExpenseRecord]:
    """
    Validate every record and run cross-record duplicate detection.
    """
    for rec in records:
        validate_record(rec)

    _detect_duplicates(records)
    return records
