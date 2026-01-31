import asyncio
import sys
import os
from fastapi import FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from playwright.async_api import async_playwright
from starlette.responses import RedirectResponse

# Windows Fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI()

# --- THE SELF-HEALING UI ---
# We store the HTML inside the code so it NEVER goes missing.
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PixelPerfect API Dashboard</title>
    <style>
        body { font-family: -apple-system, system-ui, sans-serif; background: #f4f6f8; display: flex; justify-content: center; padding-top: 50px; }
        .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); width: 500px; }
        h1 { color: #1a1a1a; margin-bottom: 20px; font-size: 24px; text-align: center; }
        label { display: block; margin-top: 15px; font-weight: 600; font-size: 14px; color: #555; }
        input[type="text"], select { width: 100%; padding: 12px; margin-top: 8px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; margin-top: 25px; padding: 14px; background: #2563eb; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:hover { background: #1d4ed8; }
        button:disabled { background: #93c5fd; cursor: not-allowed; }
        .status { margin-top: 15px; text-align: center; font-size: 14px; color: #666; height: 20px; }
    </style>
</head>
<body>
<div class="card">
    <h1>📄 PDF Generator</h1>
    <label>Website URL</label>
    <input type="text" id="urlInput" placeholder="https://www.netflix.com" value="https://www.netflix.com">
    <label>Format</label>
    <select id="formatInput">
        <option value="A4">A4</option>
        <option value="Letter">Letter</option>
    </select>
    <button onclick="generatePDF()" id="btn">Generate PDF</button>
    <div class="status" id="status"></div>
</div>
<script>
    async function generatePDF() {
        const btn = document.getElementById('btn');
        const status = document.getElementById('status');
        const url = document.getElementById('urlInput').value;
        btn.disabled = true;
        btn.innerText = "Processing...";
        status.innerText = "Starting headless browser...";
        try {
            const response = await fetch('/v1/pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_type: "url",
                    source: url,
                    format: document.getElementById('formatInput').value,
                    emulate_screen: true
                })
            });
            if (!response.ok) throw new Error("Generation failed");
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = "result.pdf";
            document.body.appendChild(a);
            a.click();
            a.remove();
            status.innerText = "Done! Downloading...";
        } catch (error) {
            status.innerText = "Error: " + error.message;
            alert("Something went wrong. Check the console.");
        } finally {
            btn.disabled = false;
            btn.innerText = "Generate PDF";
        }
    }
</script>
</body>
</html>
"""

# --- AUTO-CREATE FOLDER ON STARTUP ---
# This runs every time the server turns on.
if not os.path.exists("static"):
    os.makedirs("static")

# We write the HTML string into a real file
with open("static/index.html", "w") as f:
    f.write(DASHBOARD_HTML)

# Now we can safely mount it because we KNOW it exists
app.mount("/static", StaticFiles(directory="static"), name="static")

class PDFRequest(BaseModel):
    source_type: str = "url"
    source: str
    format: str = "A4"
    print_background: bool = True
    emulate_screen: bool = True 

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

@app.post("/v1/pdf")
async def generate_pdf(request: PDFRequest):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()

            if request.emulate_screen:
                await page.emulate_media(media="screen")

            if request.source_type == "url":
                await page.goto(request.source, wait_until="networkidle")
            elif request.source_type == "html":
                await page.set_content(request.source)

            pdf_bytes = await page.pdf(
                format=request.format,
                print_background=request.print_background,
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