# 方案1：修改 Dockerfile 使用国内代理
FROM golang:1.23-alpine AS go-builder
WORKDIR /authorizer
COPY server server
COPY Makefile .

ARG VERSION="latest"
ENV VERSION="$VERSION"

# 设置 Go 代理为国内镜像
ENV GOPROXY=https://goproxy.cn,direct
ENV GOSUMDB=sum.golang.google.cn
ENV GO111MODULE=on

RUN echo "$VERSION"
RUN apk add build-base &&\
    make clean && make && \
    chmod 777 build/server

FROM node:20-alpine AS node-builder
WORKDIR /authorizer
COPY app app
COPY dashboard dashboard
COPY Makefile .

# 设置 npm 国内镜像
RUN npm config set registry https://registry.npmmirror.com
RUN apk add build-base &&\
    make build-app && \
    make build-dashboard

# 新增：Python AI服务构建阶段
FROM python:3.11-alpine AS python-builder
WORKDIR /ai-core
COPY ai-core/ .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.douban.com/simple/ || \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ || \
    pip install --no-cache-dir -r requirements.txt

# 最终运行阶段
FROM python:3.11-alpine
RUN adduser -D -h /authorizer -u 1000 -k /dev/null authorizer
WORKDIR /authorizer

# 创建必要目录
RUN mkdir -p app dashboard ai-core

# 复制Go服务
COPY --from=go-builder --chown=authorizer:authorizer /authorizer/build build

# 复制前端资源
COPY --from=node-builder --chown=authorizer:authorizer /authorizer/app/build app/build
COPY --from=node-builder --chown=authorizer:authorizer /authorizer/app/favicon_io app/favicon_io
COPY --from=node-builder --chown=authorizer:authorizer /authorizer/dashboard/build dashboard/build
COPY --from=node-builder --chown=authorizer:authorizer /authorizer/dashboard/favicon_io dashboard/favicon_io

# 复制Python AI服务
COPY --from=python-builder --chown=authorizer:authorizer /ai-core ai-core
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# 复制模板文件
COPY templates templates

# 创建启动脚本
RUN echo '#!/bin/sh' > /authorizer/start.sh && \
    echo 'set -e' >> /authorizer/start.sh && \
    echo '' >> /authorizer/start.sh && \
    echo 'echo "Starting Authorizer services..."' >> /authorizer/start.sh && \
    echo '' >> /authorizer/start.sh && \
    echo '# 启动Python AI服务（后台运行）' >> /authorizer/start.sh && \
    echo 'echo "Starting Python AI service..."' >> /authorizer/start.sh && \
    echo 'cd /authorizer/ai-core' >> /authorizer/start.sh && \
    echo 'python grpc_server.py &' >> /authorizer/start.sh && \
    echo 'AI_PID=$!' >> /authorizer/start.sh && \
    echo 'echo "Python AI service started with PID: $AI_PID"' >> /authorizer/start.sh && \
    echo '' >> /authorizer/start.sh && \
    echo '# 等待AI服务启动' >> /authorizer/start.sh && \
    echo 'sleep 3' >> /authorizer/start.sh && \
    echo '' >> /authorizer/start.sh && \
    echo '# 启动Go服务（前台运行）' >> /authorizer/start.sh && \
    echo 'echo "Starting Go server..."' >> /authorizer/start.sh && \
    echo 'cd /authorizer' >> /authorizer/start.sh && \
    echo 'exec ./build/server' >> /authorizer/start.sh && \
    chmod +x /authorizer/start.sh

# 暴露端口
EXPOSE 8080 50051

# 切换到非root用户
USER authorizer

# 启动服务
CMD ["/bin/sh", "/authorizer/start.sh"]
