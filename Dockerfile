# Karikko, built for `linux/amd64` (see .github/workflows/release.yml). Two stages: the runtime image carries
# neither a compiler nor the build cache.
FROM python:3.12-bookworm AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
WORKDIR /app
COPY . .
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm
RUN useradd --create-home --uid 1000 karikko \
    && mkdir /data && chown karikko:karikko /data
COPY --from=build /app /app
USER karikko
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 3000

# No `VOLUME /data`: every supported run mounts a host directory. A run without a mount writes to the container
# layer, and `--rm` removes it, so a declared volume would only accumulate anonymous volumes.
ENTRYPOINT ["karikko"]
CMD ["--host=0.0.0.0", "--port=3000", "--data_dir=/data"]
