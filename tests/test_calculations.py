"""
Tests for financial calculations — ReportSummary, approved totals,
and exclusion of pending/rejected records.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from datetime import date, timedelta
from decimal import Decimal

from models.expense import ExpenseCategory, ExpenseRecord, ExpenseStatus
from services.report_service import (
    calculate_summary,
    get_approved_records,
    get_unresolved_records,
)


def _make_record(
    status: ExpenseStatus,
    amount: str = "1000.00",
    vendor: str = "Test Vendor",
    currency: str = "INR",
) -> ExpenseRecord:
    return ExpenseRecord(
        vendor=vendor,
        amount=amount,
        currency=currency,
        date=date.today() - timedelta(days=1),
        status=status,
        description="Test",
        category=ExpenseCategory.SUPPLIES,
    )


class TestSummaryCalculations(unittest.TestCase):
    """Total approved amount must only include APPROVED records with positive amounts."""

    def test_approved_total_correct(self):
        records = [
            _make_record(ExpenseStatus.APPROVED, "500.00"),
            _make_record(ExpenseStatus.APPROVED, "250.50"),
            _make_record(ExpenseStatus.PENDING, "9999.00"),
        ]
        summary = calculate_summary(records)
        self.assertEqual(summary.approved_count, 2)
        self.assertEqual(summary.total_approved_amount, Decimal("750.50"))

    def test_pending_excluded(self):
        records = [_make_record(ExpenseStatus.PENDING, "9999.00")]
        summary = calculate_summary(records)
        self.assertEqual(summary.total_approved_amount, Decimal("0"))
        self.assertEqual(summary.approved_count, 0)

    def test_rejected_excluded(self):
        records = [_make_record(ExpenseStatus.REJECTED, "5000.00")]
        summary = calculate_summary(records)
        self.assertEqual(summary.total_approved_amount, Decimal("0"))
        self.assertEqual(summary.rejected_count, 1)

    def test_needs_correction_excluded(self):
        records = [_make_record(ExpenseStatus.NEEDS_CORRECTION, "3000.00")]
        summary = calculate_summary(records)
        self.assertEqual(summary.total_approved_amount, Decimal("0"))
        self.assertEqual(summary.needs_correction_count, 1)

    def test_empty_dataset(self):
        summary = calculate_summary([])
        self.assertEqual(summary.total_records, 0)
        self.assertEqual(summary.total_approved_amount, Decimal("0"))
        self.assertEqual(summary.approved_count, 0)

    def test_decimal_precision(self):
        """Decimal arithmetic should not produce floating-point rounding errors."""
        records = [
            _make_record(ExpenseStatus.APPROVED, "0.10"),
            _make_record(ExpenseStatus.APPROVED, "0.20"),
        ]
        summary = calculate_summary(records)
        self.assertEqual(summary.total_approved_amount, Decimal("0.30"))

    def test_approved_record_with_none_amount_excluded_from_total(self):
        """Approved records with None amount should not crash the total."""
        rec = ExpenseRecord(
            vendor="Vendor",
            amount=None,
            date=date.today() - timedelta(days=1),
            status=ExpenseStatus.APPROVED,
        )
        summary = calculate_summary([rec])
        # Record is counted as approved, but contributes zero to the total
        self.assertEqual(summary.total_approved_amount, Decimal("0"))

    def test_mixed_currencies_uses_most_common(self):
        records = [
            _make_record(ExpenseStatus.APPROVED, "100", currency="INR"),
            _make_record(ExpenseStatus.APPROVED, "200", currency="INR"),
            _make_record(ExpenseStatus.APPROVED, "50", currency="USD"),
        ]
        summary = calculate_summary(records)
        self.assertEqual(summary.currency, "INR")

    def test_counts_accurate(self):
        records = [
            _make_record(ExpenseStatus.APPROVED),
            _make_record(ExpenseStatus.PENDING),
            _make_record(ExpenseStatus.NEEDS_CORRECTION),
            _make_record(ExpenseStatus.REJECTED),
            _make_record(ExpenseStatus.APPROVED),
        ]
        summary = calculate_summary(records)
        self.assertEqual(summary.total_records, 5)
        self.assertEqual(summary.approved_count, 2)
        self.assertEqual(summary.pending_count, 1)
        self.assertEqual(summary.needs_correction_count, 1)
        self.assertEqual(summary.rejected_count, 1)


class TestGetApprovedRecords(unittest.TestCase):
    """get_approved_records should only return APPROVED records with positive amounts."""

    def test_returns_only_approved(self):
        records = [
            _make_record(ExpenseStatus.APPROVED, "100"),
            _make_record(ExpenseStatus.PENDING, "200"),
            _make_record(ExpenseStatus.REJECTED, "300"),
        ]
        approved = get_approved_records(records)
        self.assertEqual(len(approved), 1)

    def test_excludes_zero_amount_approved(self):
        rec = _make_record(ExpenseStatus.APPROVED, "0")
        approved = get_approved_records([rec])
        self.assertEqual(len(approved), 0)

    def test_excludes_none_amount_approved(self):
        rec = ExpenseRecord(
            vendor="Vendor",
            amount=None,
            date=date.today() - timedelta(days=1),
            status=ExpenseStatus.APPROVED,
        )
        approved = get_approved_records([rec])
        self.assertEqual(len(approved), 0)


class TestGetUnresolvedRecords(unittest.TestCase):
    """get_unresolved_records should return PENDING and NEEDS_CORRECTION only."""

    def test_returns_pending_and_needs_correction(self):
        records = [
            _make_record(ExpenseStatus.APPROVED),
            _make_record(ExpenseStatus.PENDING),
            _make_record(ExpenseStatus.NEEDS_CORRECTION),
            _make_record(ExpenseStatus.REJECTED),
        ]
        unresolved = get_unresolved_records(records)
        statuses = {r.status for r in unresolved}
        self.assertIn(ExpenseStatus.PENDING, statuses)
        self.assertIn(ExpenseStatus.NEEDS_CORRECTION, statuses)
        self.assertNotIn(ExpenseStatus.APPROVED, statuses)
        self.assertNotIn(ExpenseStatus.REJECTED, statuses)

    def test_empty_dataset(self):
        self.assertEqual(get_unresolved_records([]), [])


if __name__ == "__main__":
    unittest.main()
