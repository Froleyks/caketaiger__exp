FROM debian:trixie-slim
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	bash \
	bzip2 \
	htop \
	ca-certificates \
	git \
	make \
	parallel \
	curl \
	ripgrep \
	gcc \
	g++ \
	cmake \
	libc6-dev \
	libgraphite2-dev \
	sbcl \
	xz-utils \
	&& rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_PYTHON_INSTALL_DIR=/app/uv-python
RUN uv venv --python 3.13
ENV PATH="/app/.venv/bin/:$PATH"
RUN uv pip install pandas matplotlib
# run
COPY . .
RUN rm -rf .git
RUN make smoketest
# Populate the TeX cache during image preparation; no experiment runs.
RUN mkdir -p /tmp/tex-cache && bin/tex.sh /tmp/tex-cache && rm -rf /tmp/tex-cache /tmp/tex-cache.pdf

CMD ["bash"]
