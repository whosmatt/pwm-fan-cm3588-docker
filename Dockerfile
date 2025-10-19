FROM python:3.13.9-alpine3.22

WORKDIR /app

COPY fan_control.py test.py LICENSE ./

ENTRYPOINT ["python3", "fan_control.py"]
