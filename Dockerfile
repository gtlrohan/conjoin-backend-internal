# Use the official Python base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the application code to the working directory
COPY . .

# Print the path to sqladmin for debugging
RUN python -c "import sqladmin; import os; print(f'sqladmin path: {os.path.dirname(sqladmin.__file__)}'); print(f'statics dir: {os.path.join(os.path.dirname(sqladmin.__file__), \"statics\")}'); print(f'statics dir exists: {os.path.exists(os.path.join(os.path.dirname(sqladmin.__file__), \"statics\"))}');"

# Ensure sqladmin static files are accessible 
RUN chmod -R 755 /usr/local/lib/python3.11/site-packages/sqladmin/statics

# Expose the port on which the application will run
EXPOSE 8080

# Run the FastAPI application using uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
