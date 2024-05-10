FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install grpcio grpcio-tools

# Generate gRPC code
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. node.proto

EXPOSE 50051

CMD ["python", "node.py"]
