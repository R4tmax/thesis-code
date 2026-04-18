FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

# Cloud Run nastaví proměnnou PORT automaticky
CMD sh -c 'streamlit run main.py --server.port=${PORT} --server.address=0.0.0.0'
