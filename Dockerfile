FROM python:3.12

WORKDIR /workspace

RUN pip config set global.index-url http://10.29.30.71/simple/
RUN pip config set global.trusted-host 10.29.30.71
RUN pip install --no-cache-dir uv

ENV UV_PYTHON_INSTALL_MIRROR=https://10.29.30.71/linux/cpython/
ENV UV_HTTP_TIMEOUT=1200
ENV UV_DEFAULT_INDEX=https://10.29.30.71/simple
ENV UV_NATIVE_TLS=true
ENV UV_INSECURE_HOST=10.29.30.71

COPY pyproject.toml .

RUN uv sync

COPY . .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/bin/bash", "entrypoint.sh"]

