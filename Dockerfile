FROM python:3.10-slim

# Install OS dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg curl unzip fonts-liberation libasound2 libatk-bridge2.0-0 \
    libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 libnss3 libxcomposite1 \
    libxdamage1 libxrandr2 xdg-utils libgtk-3-0 libxss1 libxtst6 \
    && apt-get clean

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install --with-deps

COPY . .

EXPOSE 8080
CMD ["python", "app.py"]