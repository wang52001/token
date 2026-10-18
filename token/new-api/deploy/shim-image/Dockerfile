FROM python:3.13-slim
WORKDIR /app
COPY codex_shim.py /app/codex_shim.py
ENV TZ=Asia/Shanghai
EXPOSE 3001
CMD ["python", "/app/codex_shim.py"]
