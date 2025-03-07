FROM python:3.11-slim

WORKDIR /app

# 设置时区为北京时间
RUN apt-get update && \
    apt-get install -y tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（排除 config.yaml）
COPY app/ ./app/
COPY README.md .
COPY requirements.txt .

# 设置环境变量
ENV PYTHONPATH=/app
ENV TZ=Asia/Shanghai

# 暴露端口
EXPOSE 8901

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8901"] 