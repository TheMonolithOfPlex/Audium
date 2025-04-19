# Use official lightweight Python base image
FROM python:3.10-slim

# Set working directory in the container
WORKDIR /app

# Preinstall dependencies separately to optimize Docker layer caching
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .
RUN chmod +x entrypoint.sh


# Ensure required runtime folders/files exist (if not mounted externally)
RUN mkdir -p uploads logs && \
    touch uploads.json

# Expose port used by Flask app (for documentation; actual binding is via docker-compose)
EXPOSE 9200

# Set environment variables for Flask (optional)
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Run the Flask application
CMD ["./entrypoint.sh"]
