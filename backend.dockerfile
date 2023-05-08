# Use the official Python base image with version tag
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all codes to the container
COPY . .

# Expose the port your Flask app is running on
EXPOSE 5001

# Define the command to run the application
CMD ["python", "app.py"]
