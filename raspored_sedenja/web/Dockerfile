# web/Dockerfile
FROM node:20-alpine

WORKDIR /app
# Kopiramo samo package.json da ne povučemo stari package-lock.json
COPY package.json ./
RUN npm install --no-audit --no-fund

# Sad kopiramo ostatak koda
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
