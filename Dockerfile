# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files into the container
COPY . .

# Set environment variables from .env file
COPY .env .env


EXPOSE 8005

CMD ["gunicorn","-b","0.0.0.0:8005","wsgi:app"]
