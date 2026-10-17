"""
Tests for report generation — PDF output, narrative summaries,
mock mode without API key, and AI failure handling.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from models.expense import ExpenseCategory, ExpenseRecord, ExpenseStatus
from services.pdf_service import (
    generate_narrative_summary,
    generate_pdf_report,
    _template_narrative,
)
from services.report_service import ReportSummary, calculate_summary
from services.receipt_extractor import extract_receipt, get_demo_records


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _approved_record(vendor="Test Vendor", amount="1000.00") -> ExpenseRecord:
    return ExpenseRecord(
        vendor=vendor,
        amount=amount,
        date=date.today() - timedelta(days=2),
        description="Test expense",
        category=ExpenseCategory.SUPPLIES,
        source_filename="test.jpg",
        status=ExpenseStatus.APPROVED,
    )


def _summary(records) -> ReportSummary:
    return calculate_summary(records)


# ─────────────────────────────────────────────
# PDF generation tests
# ─────────────────────────────────────────────

class TestPDFGeneration(unittest.TestCase):
    """PDF should be generated without errors and produce valid bytes."""

    def test_generates_bytes(self):
        records = [_approved_record()]
        summary = _summary(records)
        pdf = generate_pdf_report(records, summary)
        self.assertIsInstance(pdf, bytes)
        self.assertGreater(len(pdf), 100)

    def test_pdf_is_valid_pdf_header(self):
        """ReportLab output starts with %PDF-."""
        records = [_approved_record()]
        summary = _summary(records)
        pdf = generate_pdf_report(records, summary)
        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_empty_dataset_generates_pdf(self):
        """PDF should still be generated even with zero records."""
        summary = _summary([])
        pdf = generate_pdf_report([], summary)
        self.assertIsInstance(pdf, bytes)
        self.assertGreater(len(pdf), 100)

    def test_with_optional_metadata(self):
        records = [_approved_record()]
        summary = _summary(records)
        pdf = generate_pdf_report(
            records,
            summary,
            org_name="Seva Foundation",
            project_name="Rural Health 2024",
            reporting_period="October 2024",
            narrative_summary="Test narrative.",
        )
        self.assertIsInstance(pdf, bytes)

    def test_excluded_records_do_not_affect_total(self):
        """Pending/rejected records must not contribute to approved total."""
        records = [
            _approved_record(amount="500.00"),
            ExpenseRecord(
                vendor="Pending Vendor",
                amount="9999.00",
                date=date.today() - timedelta(days=1),
                status=ExpenseStatus.PENDING,
            ),
        ]
        summary = _summary(records)
        self.assertEqual(summary.total_approved_amount, Decimal("500.00"))


# ─────────────────────────────────────────────
# Narrative summary tests
# ─────────────────────────────────────────────

class TestNarrativeSummary(unittest.TestCase):
    """Template narrative should work without any API key."""

    def test_template_narrative_no_api_key(self):
        records = [_approved_record()]
        summary = _summary(records)
        text = generate_narrative_summary(records, summary, api_key=None)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 20)

    def test_template_narrative_empty_dataset(self):
        text = _template_narrative([], _summary([]))
        self.assertIn("No expenses", text)

    def test_template_narrative_mentions_approved(self):
        records = [_approved_record(amount="1234.56")]
        summary = _summary(records)
        text = _template_narrative(records, summary)
        # Should mention approved count or total
        self.assertTrue("1" in text or "approved" in text.lower())

    def test_ai_narrative_uses_fallback_on_exception(self):
        """When AI raises an exception, should fall back to template."""
        records = [_approved_record()]
        summary = _summary(records)

        with patch(
            "services.pdf_service._ai_narrative",
            side_effect=Exception("API quota exceeded"),
        ):
            text = generate_narrative_summary(
                records, summary, api_key="fake_key_xyz"
            )
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 10)


# ─────────────────────────────────────────────
# Mock mode / receipt extractor tests
# ─────────────────────────────────────────────

class TestMockMode(unittest.TestCase):
    """Mock extraction must work without any internet or API key."""

    def test_mock_extraction_no_key(self):
        """extract_receipt with no API key returns a mock record."""
        fake_image = b"\xff\xd8\xff" + b"\x00" * 100  # minimal JPEG header
        record, mode = extract_receipt(
            image_bytes=fake_image,
            filename="test_receipt.jpg",
            api_key=None,
            file_index=0,
        )
        self.assertIsNotNone(record)
        self.assertEqual(mode, "mock")
        self.assertEqual(record.extraction_mode, "mock")

    def test_mock_record_has_source_filename(self):
        fake_image = b"\x89PNG" + b"\x00" * 100
        record, _ = extract_receipt(
            image_bytes=fake_image,
            filename="my_receipt.png",
            api_key=None,
            file_index=1,
        )
        self.assertEqual(record.source_filename, "my_receipt.png")

    def test_demo_records_not_empty(self):
        records = get_demo_records()
        self.assertGreater(len(records), 0)

    def test_demo_records_have_source_filenames(self):
        records = get_demo_records()
        for rec in records:
            self.assertTrue(rec.source_filename, "Source filename should not be empty")

    def test_ai_failure_falls_back_to_mock(self):
        """When AI is configured but fails, extraction falls back to mock gracefully."""
        fake_image = b"\xff\xd8\xff" + b"\x00" * 100

        with patch(
            "services.receipt_extractor._extract_with_gemini",
            side_effect=Exception("Connection timeout"),
        ):
            record, mode = extract_receipt(
                image_bytes=fake_image,
                filename="fail_receipt.jpg",
                api_key="fake_key",
                file_index=0,
            )

        self.assertIsNotNone(record)
        self.assertIn("mock", mode)
        self.assertIn("mock", record.extraction_mode)


# ─────────────────────────────────────────────
# Config / no-key mode test
# ─────────────────────────────────────────────

class TestConfigNoKey(unittest.TestCase):
    """Application config should detect demo mode when no key is present."""

    def test_demo_mode_without_key(self):
        import importlib
        import utils.config as config_mod

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_API_KEY", None)
            importlib.reload(config_mod)
            cfg = config_mod.get_config()
            self.assertIsNone(cfg.gemini_api_key)
            self.assertTrue(cfg.is_demo_mode)


if __name__ == "__main__":
    unittest.main()
