# Sample Data

This folder is for storing sample receipt images and test documents.

## Included demo dataset

The application ships with a built-in **Demo Dataset** of 8 realistic, fictional NGO expense records. You can load them directly from the *Upload Receipts* page without uploading any files.

The demo dataset intentionally includes:

- ✅ Valid records (correct date, vendor, amount, description, category)
- 🟡 Records with warnings (missing receipt number, unclassified category)
- 🔴 Records with errors (missing vendor name, negative amount)
- ⚠️ A near-duplicate pair (same date, vendor, and amount)

This allows judges and evaluators to explore the full review → validate → approve → report workflow without any real data.

## Adding your own sample receipts

Place PNG, JPG, or JPEG receipt images in this folder. You can then upload them through the *Upload Receipts* page in the application.

**Note:** Do not commit real receipts, personal financial data, or sensitive documents to version control.
