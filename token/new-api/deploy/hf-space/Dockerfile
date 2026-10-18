# Hugging Face Space 一体化镜像：new-api(3000 内部) + 身份伪装 shim(7860 对外)
FROM calciumion/new-api:latest
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
COPY codex_shim.py /opt/codex_shim.py
COPY start.sh /start.sh
RUN chmod +x /start.sh && chmod -R 777 /data
ENV TZ=Asia/Shanghai
EXPOSE 7860
CMD ["/start.sh"]
