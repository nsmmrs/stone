FROM python:2.7-slim

RUN pip install --no-cache-dir jinja2 ply

CMD ["bash"]
