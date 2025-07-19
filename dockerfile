FROM python:3.9-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    TZ=Asia/Shanghai

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝所有代码
COPY . .

# gunicorn启动包内app，需指定包路径
RUN mkdir -p /app/app/data
CMD ["gunicorn", "--chdir", "app", "-b", "0.0.0.0:5000", "app:create_app()"]