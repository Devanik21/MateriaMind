.PHONY: setup test run

setup:
	pip install -r requirements.txt

test:
	pytest tests/

run:
	streamlit run app.py
