# Use official lightweight Python base image
FROM python:3.10-slim

# Set working directory in the container
WORKDIR /app

# Preinstall dependencies separately to optimize Docker layer caching
COPY requirements.txt /app/requirements.txt
# Use a build argument to toggle caching
ARG PIP_NO_CACHE=true
RUN if [ "$PIP_NO_CACHE" = "true" ]; then pip install --no-cache-dir -r requirements.txt; else pip install -r requirements.txt; fi
# Copy the rest of the application code into the container
COPY . .
RUN if [ -f entrypoint.sh ]; then chmod +x entrypoint.sh; else echo "Error: entrypoint.sh not found" && exit 1; fi


# Ensure required runtime folders/files exist (if not mounted externally)
RUN mkdir -p uploads logs && \
    ( [ -w uploads ] || (echo "Error: 'uploads' directory is not writable" && exit 1) ) && \
    touch uploads/uploads.json
# Expose port used by Flask app for documentation purposes only.
# Note: This does not publish the port; it is purely informational.
# Actual port binding must be explicitly configured using `docker run -p` or in `docker-compose.yml`.
EXPOSE 9200
# Set unbuffered output for debugging; can be overridden at runtime
ENV PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-1}
# Set environment variables for Flask (optional)
# Set Flask environment to production mode
ENV FLASK_ENV=production
CMD ["bash", "-c", "[ -f ./entrypoint.sh ] && ./entrypoint.sh || (echo 'Entrypoint script failed. Check logs for details.' | tee /app/entrypoint_error.log && exit 1)"]
