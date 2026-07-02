# Stage 1: Build the Vue 3 Frontend
FROM node:24.14.1-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

# Copy source and build
COPY frontend/ .
RUN npm run build

# Stage 2: Build the Django Backend
FROM python:3.13.12-slim
WORKDIR /app

COPY requirements.txt ./

# Install Python dependencies, plus gunicorn
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy backend code
COPY backend/ ./backend/

# Copy the built static files from Stage 1 into the expected Django directory
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Set dummy environment variables strictly to allow collectstatic to run during build
ENV DJANGO_SETTINGS_MODULE="time_tracker.settings"
ENV SECRET_KEY="dummy-key-for-collectstatic"
ENV DEBUG="False"

RUN cd backend && python manage.py collectstatic --noinput

COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

# Start Gunicorn WSGI server
CMD ["gunicorn", "--chdir", "backend", "time_tracker.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4"]
