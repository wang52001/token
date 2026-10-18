# Koyeb 一体化镜像：new-api + 双端隔离网关（单端口 Host 分流）同容器运行
# 构建上下文 = 仓库根目录，Dockerfile 路径 = koyeb/Dockerfile
# 镜像版本与本地实测二进制一致（v1.0.0-rc.35），路由白名单按此版本收口
FROM calciumion/new-api:v1.0.0-rc.35

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

COPY gateway /opt/gateway
COPY koyeb/start.sh /start.sh
RUN chmod +x /start.sh

ENV TZ=Asia/Shanghai \
    USER_DOMAIN=new-api.jdhsf.top \
    ADMIN_DOMAIN=new-api-admin.jdhsf.top \
    USER_LOG_FILE=/tmp/gateway-user.log \
    ADMIN_LOG_FILE=/tmp/gateway-admin.log
# ADMIN_GATEWAY_PASS 必须在平台环境变量里设置（不随镜像/仓库分发）

# 对外只暴露网关（$PORT）；new-api 在容器内 127.0.0.1:3000
EXPOSE 3001
# 基础镜像自带 ENTRYPOINT ["/new-api"]，必须覆盖，否则 start.sh 会被当成
# new-api 的参数执行，网关根本不会启动（流量绕过网关直达管理面！）
ENTRYPOINT ["/bin/sh", "/start.sh"]
