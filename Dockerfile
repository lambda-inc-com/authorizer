# 方案1：修改 Dockerfile 使用国内代理
FROM golang:1.21.3-alpine3.18 as go-builder
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

FROM node:20-alpine3.18 as node-builder
WORKDIR /authorizer
COPY app app
COPY dashboard dashboard
COPY Makefile .

# 设置 npm 国内镜像
RUN npm config set registry https://registry.npmmirror.com
RUN apk add build-base &&\
    make build-app && \
    make build-dashboard

FROM alpine:3.18
RUN adduser -D -h /authorizer -u 1000 -k /dev/null authorizer
WORKDIR /authorizer
RUN mkdir app dashboard
COPY --from=node-builder --chown=nobody:nobody /authorizer/app/build app/build
COPY --from=node-builder --chown=nobody:nobody /authorizer/app/favicon_io app/favicon_io
COPY --from=node-builder --chown=nobody:nobody /authorizer/dashboard/build dashboard/build
COPY --from=node-builder --chown=nobody:nobody /authorizer/dashboard/favicon_io dashboard/favicon_io
COPY --from=go-builder --chown=nobody:nobody /authorizer/build build
COPY templates templates
EXPOSE 8080
USER authorizer
CMD [ "./build/server" ]
