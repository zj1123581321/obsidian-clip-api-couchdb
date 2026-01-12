FROM python:3.11-slim

WORKDIR /app

# 设置时区为北京时间并更新系统 CA 证书
RUN apt-get update && \
    apt-get install -y tzdata ca-certificates curl && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    update-ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 复制依赖配置文件
COPY pyproject.toml .

# 使用 uv 安装依赖（不创建虚拟环境，直接安装到系统）
RUN uv pip install --system --no-cache -r pyproject.toml

# 复制应用代码（排除 config.yaml）
COPY app/ ./app/
COPY README.md .

# 设置环境变量
ENV PYTHONPATH=/app
ENV TZ=Asia/Shanghai
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# 暴露端口
EXPOSE 8901

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8901"]
