FROM python:3.8-slim AS builder

ADD relies_on.py /app/relies_on.py
ADD requirements.txt /app/requirements.txt
ADD action.yml /app/action.yml

WORKDIR /app

RUN pip install --target=/app -r /app/requirements.txt

# A distroless container image with Python and some basics like SSL certificates
# https://github.com/GoogleContainerTools/distroless
FROM gcr.io/distroless/python3-debian10
COPY --from=builder /app /app
WORKDIR /app
ENV PYTHONPATH /app
CMD ["/app/relies_on.py"]
