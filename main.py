import asyncio
import sys
from typing import Optional
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright

# --- WINDOWS FIX ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# -------------------

app = FastAPI(title="Pixel-Perfect PDF API")

# --- DATA MODELS (The Interface) ---
# This defines what the user MUST send us.
class PDFRequest(BaseModel):
    source_type: str  # Must be "url" or "html"
    source: str       # The link OR the raw HTML string
    
    # Options (with defaults)
    format: str = "A4"          # "Letter", "Legal", etc.
    landscape: bool = False
    print_background: bool = True # Crucial for CSS colors
    wait_for_network: bool = False # Wait for charts/images to load?

@app.get("/")
async def root():
    return {"message": "PDF API v1 is ready. Use POST /v1/pdf"}

@app.post("/v1/pdf")
async def generate_pdf(request: PDFRequest):
    """
    Professional Endpoint: Takes JSON, returns a downloadable PDF.
    """
    try:
        async with async_playwright() as p:
            # 1. Launch Browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 2. Input Handling (The Switch)
            if request.source_type == "url":
                # For Dashboards/Legal: Go to the website
                # "networkidle" means "wait until network traffic stops" (good for charts)
                wait_strategy = "networkidle" if request.wait_for_network else "load"
                await page.goto(request.source, wait_until=wait_strategy)
                
            elif request.source_type == "html":
                # For Invoices/Receipts: Load raw HTML
                await page.set_content(request.source)
            
            else:
                raise HTTPException(status_code=400, detail="source_type must be 'url' or 'html'")

            # 3. Generate PDF (The Render)
            pdf_bytes = await page.pdf(
                format=request.format,
                landscape=request.landscape,
                print_background=request.print_background
            )
            
            await browser.close()

            # 4. Return as Download (The Fix)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    # This forces the browser to download the file named "output.pdf"
                    "Content-Disposition": "attachment; filename=document.pdf"
                }
            )

    except Exception as e:
        print(f"Error: {str(e)}") # Log to console
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)