import asyncio
import sys
from fastapi import FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles # <--- NEW: To serve your UI
from pydantic import BaseModel
from playwright.async_api import async_playwright

# Windows Fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI()

# --- 1. SERVE THE UI (The Playground) ---
# We tell FastAPI: "If someone asks for a file, look in the 'static' folder"
app.mount("/static", StaticFiles(directory="static"), name="static")

class PDFRequest(BaseModel):
    source_type: str = "url"
    source: str
    format: str = "A4"
    print_background: bool = True
    # New option to trick the website
    emulate_screen: bool = True 

@app.get("/")
async def root():
    # Redirect root to our new fancy UI
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

@app.post("/v1/pdf")
async def generate_pdf(request: PDFRequest):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                # TRICK 1: Set a huge viewport so grids don't collapse
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()

            # TRICK 2: Force "Screen" media type (Ignore Print CSS)
            if request.emulate_screen:
                await page.emulate_media(media="screen")

            # Go to content
            if request.source_type == "url":
                await page.goto(request.source, wait_until="networkidle")
            elif request.source_type == "html":
                await page.set_content(request.source)

            # Generate PDF
            pdf_bytes = await page.pdf(
                format=request.format,
                print_background=request.print_background,
                # TRICK 3: Scale it slightly so A4 doesn't cut off wide content
                scale=0.8,
                margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"}
            )
            
            await browser.close()

            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=output.pdf"}
            )

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)