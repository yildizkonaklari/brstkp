FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source
COPY . .

# Exposure
EXPOSE 3000

# Start dev server
CMD ["npm", "run", "dev"]
