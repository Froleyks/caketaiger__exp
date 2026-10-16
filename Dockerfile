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
	&& if [ "$(uname -m)" != x86_64 ]; then \
		apt-get install -y --no-install-recommends qemu-user; fi \
	&& rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_PYTHON_INSTALL_DIR=/app/uv-python
RUN uv venv --python 3.13
ENV PATH="/app/.venv/bin/:$PATH"
RUN uv pip install pandas matplotlib

# run
COPY . .
# Plotting all from our data caches the fonts tectonic needs offline.
RUN rm -rf .git && make smoketest && make clean && make our-data \
	&& make all && make clean && make our-data

CMD ["bash"]
