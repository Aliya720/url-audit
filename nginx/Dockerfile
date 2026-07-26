# Nginx Dockerfile — TRD §14
# Serves React static build at /, proxies /api/* to Django
FROM nginx:1.27-alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config
COPY nginx.conf /etc/nginx/conf.d/

# Create directory for React build (will be volume-mounted or copied)
RUN mkdir -p /usr/share/nginx/html

EXPOSE 80
