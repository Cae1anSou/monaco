# Simple Vue3 + Vite sandbox image
FROM node:18-alpine as build
WORKDIR /app

# Install deps separately for cache
COPY package*.json ./
RUN npm install --silent

# Copy source
COPY . .

# Expose dev server port
EXPOSE 5173

# Start Vite dev server (host 0.0.0.0 so container port is accessible)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
