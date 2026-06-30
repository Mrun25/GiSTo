import httpx
import asyncio
import sys

async def main():
    base_url = "http://localhost:8000"
    client = httpx.AsyncClient(base_url=base_url)
    
    # 1. Health check
    res = await client.get("/health")
    assert res.status_code == 200, "Health check failed"
    print("Health check OK")
    
    # Let's get the CA and Business from seed data
    MOCK_CA_ID = '9365dcba-d858-45ad-beaa-67ab8ef097ea'
    MOCK_BUSINESS_ID = 'f1e40eb1-dcaf-4cf8-8c1d-1b1509355157'
    
    # 2. Test CA Portfolio
    res = await client.get(f"/ca/{MOCK_CA_ID}/portfolio")
    assert res.status_code == 200, f"CA Portfolio failed: {res.text}"
    print("CA Portfolio fetch OK")
    
    # 3. Test Business details (without CA)
    res = await client.get(f"/businesses/{MOCK_BUSINESS_ID}")
    assert res.status_code == 200, f"Business Detail failed: {res.text}"
    print("Business Detail fetch OK")
    
    # 4. Test Business Invoices
    res = await client.get(f"/invoices/by-business/{MOCK_BUSINESS_ID}")
    assert res.status_code == 200, f"Business Invoices failed: {res.text}"
    print("Business Invoices fetch OK")
    
    # 5. Test Business Suppliers
    res = await client.get(f"/businesses/{MOCK_BUSINESS_ID}/suppliers")
    assert res.status_code == 200, f"Business Suppliers failed: {res.text}"
    print("Business Suppliers fetch OK")
    
    # 6. Test extracting invoice (Bot logic test)
    # We will upload a dummy file to the extract endpoint
    files = {'file': ('dummy.pdf', b'dummy content', 'application/pdf')}
    res = await client.post("/invoices/extract", files=files)
    assert res.status_code == 200, f"Invoice extraction failed: {res.text}"
    print("Invoice Extraction OK")

    print("All tests passed!")
    
if __name__ == "__main__":
    asyncio.run(main())
