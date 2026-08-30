# Build step
FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Terima build arguments dari Railway
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

ARG VITE_WS_URL
ENV VITE_WS_URL=$VITE_WS_URL

RUN npm run build

# Serve step dengan Nginx
FROM nginx:alpine

# Copy hasil build react ke folder public nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx config untuk SPA (mengatasi error 404 saat refresh react-router)
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
