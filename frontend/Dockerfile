# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

FROM node:20-slim
WORKDIR /app
COPY frontend/package.json .
RUN npm install
COPY frontend/ .
CMD ["npm", "start"]
