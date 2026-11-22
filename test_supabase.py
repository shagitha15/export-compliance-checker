import json
import sys
from supabase_service import store_extracted_document, fetch_extracted_documents

def test_insert_and_verify():
    filename = "commercial_invoice_01.pdf"
    document_type = "Commercial Invoice"
    extracted_data = {
        "invoice_number": "INV-2024-001",
        "total_invoice_amount": 22500.0,
        "currency": "EUR"
    }

    print(f"1. Calling store_extracted_document for '{filename}'...")
    try:
        inserted = store_extracted_document(
            filename=filename,
            document_type=document_type,
            extracted_data=extracted_data,
        )
    except Exception as e:
        print(f"Error inserting record: {e}", file=sys.stderr)
        sys.exit(1)

    record_id = inserted.get("id")
    print(f"Successfully inserted! Record ID: {record_id}")
    print(f"Full inserted record: {json.dumps(inserted, indent=2, default=str)}")

    print(f"\n2. Verifying record in Supabase...")
    try:
        results = fetch_extracted_documents(filename=filename, limit=1)
        if results:
            print("Verified! Found record in Supabase:")
            print(json.dumps(results[0], indent=2, default=str))
        else:
            print("Warning: Inserted record not found on query.")
    except Exception as e:
        print(f"Error fetching record: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    test_insert_and_verify()
