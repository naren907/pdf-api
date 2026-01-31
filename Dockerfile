# 1. Start with the official Python image that includes Playwright browsers
# This saves us from having to install Chrome manually!
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy our "Shopping List" into the container
COPY requirements.txt .

# 4. Install the Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy our actual code (main.py) into the container
COPY main.py .

# 6. Open the door (Port 8000) so we can talk to the API
EXPOSE 8000

# 7. The command to run when the container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]