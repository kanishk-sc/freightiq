FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY tsconfig*.json eslint.config.js ./
COPY src ./src
RUN npm run build

FROM build AS test
COPY tests ./tests
CMD ["npm", "test"]

FROM node:22-bookworm-slim AS runtime
ENV NODE_ENV=production HOST=0.0.0.0 PORT=8001
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist
USER node
EXPOSE 8001
CMD ["node", "dist/server.js"]
