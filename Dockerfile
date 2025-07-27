FROM python:3.10-slim

# Install OS dependencies required by Chromium (headless)
RUN apt-get update && apt-get install -y \
    wget gnupg curl unzip fonts-liberation libasound2 libatk-bridge2.0-0 \
    libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 libnss3 libxcomposite1 \
    libxdamage1 libxrandr2 xdg-utils libgtk-3-0 libxss1 libxtst6 \
    && apt-get clean

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install Chromium only
RUN python -m playwright install chromium

# Copy all app files
COPY . .

# Expose the Flask port
EXPOSE 8080

# Start the app
CMD ["python", "app.py"]
