"""
Tests for validation logic — field-level checks, duplicate detection,
and status transitions.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from datetime import date, timedelta
from decimal import Decimal

from models.expense import ExpenseCategory, ExpenseRecord, ExpenseStatus
from services.validation_service import validate_all, validate_record


class TestMissingFields(unittest.TestCase):
    """Records with missing required fields should get error-level issues."""

    def test_missing_vendor(self):
        rec = ExpenseRecord(
            vendor="",
            amount=Decimal("100"),
            date=date.today() - timedelta(days=1),
        )
        validate_record(rec)
        fields = [i.field for i in rec.validation_issues]
        self.assertIn("vendor", fields)

    def test_missing_date(self):
        rec = ExpenseRecord(vendor="Test Shop", amount=Decimal("100"), date=None)
        validate_record(rec)
        fields = [i.field for i in rec.validation_issues]
        self.assertIn("date", fields)

    def test_missing_amount(self):
        rec = ExpenseRecord(
            vendor="Test Shop",
            date=date.today() - timedelta(days=1),
            amount=None,
        )
        validate_record(rec)
        fields = [i.field for i in rec.validation_issues]
        self.assertIn("amount", fields)

    def test_all_fields_present_no_errors(self):
        rec = ExpenseRecord(
            vendor="Test Shop",
            amount=Decimal("500"),
            date=date.today() - timedelta(days=2),
            description="Test purchase",
            category=ExpenseCategory.SUPPLIES,
        )
        validate_record(rec)
        errors = [i for i in rec.validation_issues if i.severity == "error"]
        self.assertEqual(errors, [])


class TestInvalidAmounts(unittest.TestCase):
    """Non-positive amounts must be flagged."""

    def test_zero_amount(self):
        rec = ExpenseRecord(
            vendor="Shop",
            date=date.today() - timedelta(days=1),
            amount=Decimal("0"),
        )
        validate_record(rec)
        fields = [i.field for i in rec.validation_issues if i.severity == "error"]
        self.assertIn("amount", fields)

    def test_negative_amount(self):
        rec = ExpenseRecord(
            vendor="Shop",
            date=date.today() - timedelta(days=1),
            amount=Decimal("-100"),
        )
        validate_record(rec)
        fields = [i.field for i in rec.validation_issues if i.severity == "error"]
        self.assertIn("amount", fields)

    def test_positive_amount_no_error(self):
        rec = ExpenseRecord(
            vendor="Shop",
            date=date.today() - timedelta(days=1),
            amount=Decimal("0.01"),
        )
        validate_record(rec)
        amount_errors = [i for i in rec.validation_issues if i.field == "amount" and i.severity == "error"]
        self.assertEqual(amount_errors, [])


class TestInvalidDates(unittest.TestCase):
    """Future dates should generate a warning."""

    def test_future_date_warning(self):
        rec = ExpenseRecord(
            vendor="Shop",
            amount=Decimal("100"),
            date=date.today() + timedelta(days=5),
        )
        validate_record(rec)
        date_issues = [i for i in rec.validation_issues if i.field == "date"]
        self.assertTrue(len(date_issues) > 0)

    def test_past_date_ok(self):
        rec = ExpenseRecord(
            vendor="Shop",
            amount=Decimal("100"),
            date=date.today() - timedelta(days=1),
        )
        validate_record(rec)
        date_errors = [i for i in rec.validation_issues if i.field == "date" and i.severity == "error"]
        self.assertEqual(date_errors, [])


class TestDuplicateDetection(unittest.TestCase):
    """Duplicate records should be flagged."""

    def _base_record(self, **kwargs):
        defaults = {
            "vendor": "Duplicate Shop",
            "amount": Decimal("999"),
            "date": date.today() - timedelta(days=1),
            "description": "Test",
            "category": ExpenseCategory.SUPPLIES,
        }
        defaults.update(kwargs)
        return ExpenseRecord(**defaults)

    def test_exact_duplicate_flagged(self):
        r1 = self._base_record(source_filename="receipt_01.jpg")
        r2 = self._base_record(source_filename="receipt_02.jpg")
        validate_all([r1, r2])
        dup_issues_r2 = [i for i in r2.validation_issues if i.field == "duplicate"]
        self.assertTrue(len(dup_issues_r2) > 0)

    def test_different_vendors_not_duplicate(self):
        r1 = self._base_record(vendor="Shop A")
        r2 = self._base_record(vendor="Shop B")
        validate_all([r1, r2])
        dup_issues = [i for i in r2.validation_issues if i.field == "duplicate"]
        self.assertEqual(dup_issues, [])

    def test_duplicate_receipt_number(self):
        r1 = self._base_record(receipt_number="INV-001", vendor="Alpha")
        r2 = self._base_record(receipt_number="INV-001", vendor="Beta")
        validate_all([r1, r2])
        rn_issues = [i for i in r2.validation_issues if i.field == "receipt_number"]
        self.assertTrue(len(rn_issues) > 0)

    def test_single_record_no_duplicate(self):
        r = self._base_record()
        validate_all([r])
        dup_issues = [i for i in r.validation_issues if i.field == "duplicate"]
        self.assertEqual(dup_issues, [])

    def test_empty_list(self):
        """validate_all on empty list should not raise."""
        result = validate_all([])
        self.assertEqual(result, [])


class TestStatusTransitions(unittest.TestCase):
    """Status should update correctly based on validation results."""

    def test_pending_with_errors_becomes_needs_correction(self):
        # Record with no date, vendor, or amount — will have errors
        rec = ExpenseRecord(status=ExpenseStatus.PENDING)
        validate_record(rec)
        self.assertEqual(rec.status, ExpenseStatus.NEEDS_CORRECTION)

    def test_approved_record_stays_approved(self):
        rec = ExpenseRecord(
            vendor="Good Shop",
            amount=Decimal("100"),
            date=date.today() - timedelta(days=1),
            status=ExpenseStatus.APPROVED,
        )
        validate_record(rec)
        # validate_record must not downgrade an already-APPROVED record
        self.assertEqual(rec.status, ExpenseStatus.APPROVED)


if __name__ == "__main__":
    unittest.main()
