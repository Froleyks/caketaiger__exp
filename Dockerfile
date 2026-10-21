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

# Fetch and build Poly/ML
RUN git clone --branch v5.9.2 --depth 1 https://github.com/polyml/polyml.git /tmp/polyml \
    && cd /tmp/polyml \
    && ./configure --prefix=/usr \
    && make -j"$(nproc)" \
    && make install \
    && ldconfig \
    && rm -rf /tmp/polyml

# Build HOL and Caketaiger first, cached independently of the rest of the project
RUN git clone --branch trindemossen-2-v9 --depth 1 https://github.com/HOL-Theorem-Prover/HOL.git formalization/HOL \
    && test "$(git -C formalization/HOL rev-parse HEAD)" = 652d1f0aad5cd537ed1e5d470ba3444e70ba470e \
    && git clone --branch caketaiger-artifact --depth 1 https://github.com/CakeML/cakeml.git formalization/cakeml \
    && test "$(git -C formalization/cakeml rev-parse HEAD)" = 4ab8ec5f0c933aa9a0229e760907a71485f9e950
RUN cd formalization/HOL && poly < tools/smart-configure.sml && bin/build
ENV PATH="/app/formalization/HOL/bin:$PATH"
# --retry-oos retries when PolyML runs out of store for some reason
RUN cd formalization/cakeml/examples/hwmcc_checker \
    && Holmake --retry-oos=5
# We only want to produce the .S files, not the binary, because the caketaiger
# recipe included by default does not account for the x86/ARM64 split
RUN cd formalization/cakeml/examples/hwmcc_checker/compilation \
    && Holmake --retry-oos=5 caketaigerCompileTheory.uo caketaigerARM8CompileTheory.uo
RUN cd formalization/cakeml/examples/hwmcc_checker/compilation/proofs \
    && Holmake --retry-oos=5

# run
COPY . .
# Plotting all from our data caches the fonts tectonic needs offline.
RUN rm -rf .git && make smoketest && make all && make clean && make our-data

CMD ["bash"]
