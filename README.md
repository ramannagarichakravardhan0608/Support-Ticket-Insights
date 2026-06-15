# Support Ticket Assistant

An AI-powered support ticket assistant built with Streamlit, FastAPI, pandas, and the Hugging Face Inference API.

## Features

- Loads support tickets from `support_tickets.xlsx`
- Converts natural-language questions into structured JSON operations using an LLM
- Executes the operation on the dataframe
- Returns a clear answer through a REST API

## Architecture

```text
Streamlit UI or API client
  |
  v
LLM planner via Hugging Face Inference API
  |
  v
JSON action plan
  |
  v
Query Engine on pandas dataframe
  |
  v
Answer
```

## Project Structure

```text
project/
├── app/
│   ├── main.py
│   ├── llm.py
│   ├── data_loader.py
│   ├── query_engine.py
│   ├── config.py
│   └── utils.py
├── support_tickets.xlsx
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Installation

1. Use Python 3.11 or newer.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Hugging Face Setup Instructions

1. Create a Hugging Face account if you want to use the hosted model path.
2. Set `HF_API_KEY` and `HF_MODEL_NAME` in your shell, or edit `app/config.py` to load them from your preferred secret store.
3. If neither value is set, the app uses the built-in heuristic planner instead of calling Hugging Face.

If you do want to configure a token manually, make sure it is not committed to the repository. A local-only example is:

```python
HF_API_KEY = "your_token_here"
```

Keep `MODEL_NAME` set to a free Inference API model such as:

```python
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
```

## Running Locally

Start the Streamlit frontend with one command:

```bash
streamlit run streamlit_app.py
```

If you want the API instead:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Running with Docker

Build and start the service:

```bash
docker-compose up --build
```

This current Docker setup runs the FastAPI backend. If you want a Streamlit container, the command can be switched to `streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0`.

## API Examples

### Health Check

```bash
curl http://localhost:8000/
```

Response:

```json
{"status":"ok","rows_loaded":500}
```

### Query Support Tickets

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"How many open tickets are there?"}'
```

Response:

```json
{"answer":"There are 24 tickets matching status=Open."}
```

Other example questions:

- `Show high priority tickets.`
- `Which agent resolved the most tickets?`
- `List unresolved tickets.`
- `What are the common issues reported?`

## Streamlit Frontend

The Streamlit UI provides:

- a natural-language question box
- example question buttons
- dataset summary charts
- a preview table of the first rows

It reuses the same dataframe operations and Hugging Face planning logic as the API.

## Assumptions

- The workbook contains columns similar to:
  - `ticket_id`
  - `created_at`
  - `category`
  - `priority`
  - `status`
  - `response_time_hrs`
  - `resolution_time_hrs`
  - `agent_id`
  - `customer_rating`
  - `issue_summary`
- `Open` and `Escalated` are treated as unresolved ticket statuses.
- `Resolved` tickets are used for the top-agent calculation.
- Common issues are computed from repeated `issue_summary` values.

## Notes

- The application loads the Excel file once at startup.
- The LLM must return JSON. The backend parses that JSON and executes the corresponding dataframe operation.
- No `.env` file is used. The Hugging Face API key is read from `app/config.py`.
