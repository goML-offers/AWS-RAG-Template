# THE DOCKERFILE TO BE USED FOR PRODUCTION.
# BASE WORKING DOCKERFILE EXAMPLE:
    
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application code into the container
COPY . .


# Command to start the FastAPI application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
