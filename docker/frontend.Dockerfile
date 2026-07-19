# syntax=docker/dockerfile:1
# Frontend image — Next.js App Router shell (T-0.09).
# Dev server for local Compose; production build comes in a later task.

FROM node:20-alpine

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

COPY frontend/package.json ./
RUN npm install

COPY frontend ./
COPY docker/frontend.entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
  && sed -i 's/\r$//' /entrypoint.sh

EXPOSE 3000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", "3000"]
