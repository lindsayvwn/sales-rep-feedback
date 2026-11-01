# Sales Rep Feedback

A Streamlit app for a car dealership. Customers rate their sales rep and leave a comment; an LLM (via Groq) labels each comment; the owner page shows what to coach reps on.

**Business question:** Which sales-rep behaviors should we coach on to raise customer ratings?

## Labels

| Label | Definition |
|---|---|
| helpful | The rep was knowledgeable, friendly, or helped the customer find the right car. |
| pushy | The rep used high-pressure tactics, rushed the customer, or pushed add-ons they didn't want. |
| communication | The rep was slow to respond, didn't follow up, didn't listen, or was hard to reach. |
| pricing | The rep was unclear or misleading about price, fees, trade-in value, or financing. |

A comment goes to manual review when the model returns something outside these labels (`unclear`), or when the stars and label disagree (`helpful` with 1–2 stars, a complaint with 5 stars).

## Run locally

1. Put your Groq key in `.streamlit/secrets.toml` (this file is git-ignored).
2. `pip install -r requirements.txt`
3. `streamlit run app.py`

## Deploy

On Streamlit Cloud, point the app at `app.py` in this repo and paste `GROQ_API_KEY = "..."` into **App settings → Secrets**.
