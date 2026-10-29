# Lambda の標準ランタイム(AL2023, glibc 2.34)では lore-vcs の .so(glibc 2.39 要求)が読めないため、
# Debian trixie(glibc 2.41)を基盤にしたコンテナイメージ方式の Lambda で動かす。
FROM public.ecr.aws/docker/library/python:3.13-slim-trixie
RUN pip install --no-cache-dir awslambdaric boto3 "lore-vcs==0.11.0"
WORKDIR /var/task
COPY handler.py .
ENTRYPOINT ["python", "-m", "awslambdaric"]
CMD ["handler.handler"]
