FROM python:3-alpine

WORKDIR /app

COPY requirements.txt /app

RUN pip install -r requirements.txt

COPY . /app

RUN mv src/* /app

#RUN uv pip install -r requirements.txt
#RUN uv sync

#ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]

