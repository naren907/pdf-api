import asyncio
import sys

# Windows Fix (Keep this!)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.responses import Response # <--- NEW IMPORT
from playwright.async_api import async_playwright

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "PDF Generator is running!"}

@app.get("/generate-pdf")
async def generate_pdf(url: str):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(url)
            
            # Snap the PDF
            pdf_bytes = await page.pdf(format="A4", print_background=True)
            
            await browser.close()
            
            # --- THE CHANGE ---
            # Instead of returning JSON text, we return the raw file bytes.
            # media_type="application/pdf" tells the browser "This is a PDF, please display it."
            return Response(content=pdf_bytes, media_type="application/pdf")
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)