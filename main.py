import asyncio
import sys

# --- THE NUCLEAR FIX ---
# We force this policy to apply globally, immediately upon file load.
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# -----------------------

from fastapi import FastAPI
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
            
            pdf = await page.pdf(format="A4", print_background=True)
            
            await browser.close()
            
            return {"status": "success", "pdf_size_bytes": len(pdf)}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)