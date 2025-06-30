# Use an official Python runtime as a parent image
FROM python:3.13-slim-bookworm

# Set environment variables for non-interactive Python and build processes
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Set the working directory in the container
WORKDIR /app

# Install uv as root (system-wide within the container)
RUN python -m pip install --no-cache-dir uv

# Install system dependencies for psycopg
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*


# Create a non-root user and set up their environment
RUN adduser --system --group --home /home/appuser --disabled-password appuser \
    && chown -R appuser:appuser /app

# Set the HOME environment variable for the non-root user
ENV HOME /home/appuser

# Add the system-wide Python bin directory to appuser's PATH
# This ensures uv (installed by root) is found by appuser
ENV PATH="/usr/local/bin:${PATH}" 
# Assuming uv installs to /usr/local/bin

# Switch to the non-root user for subsequent commands
USER appuser

# Copy only the dependency files first to leverage Docker's build cache
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

# Install project dependencies using uv from the lockfile
RUN uv sync --no-cache

# Copy the rest of the application code
COPY --chown=appuser:appuser . .

# Expose the ports the services will run on
EXPOSE 4200

# Command to run the server
CMD ["uv", "run", "src/bigquery/server.py"]