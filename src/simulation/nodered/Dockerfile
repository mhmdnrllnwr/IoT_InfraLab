FROM nodered/node-red:4.0.8

# Pre-install required palette nodes at build time
# This avoids runtime npm install failures and ensures reproducible builds
COPY NodeRed_Data/package.json /data/package.json
RUN npm install --omit=dev --no-audit --no-fund --prefix /data && \
    npm cache clean --force

# Copy flows and settings (overridable by /data volume mount at runtime)
COPY NodeRed_Data/settings.js /data/settings.js
COPY NodeRed_Data/flows.json /data/flows.json
