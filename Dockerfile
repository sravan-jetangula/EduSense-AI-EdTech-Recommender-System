FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501
EXPOSE 8000

CMD bash -c "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0"