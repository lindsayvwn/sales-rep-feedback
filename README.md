# Sales Rep Feedback

A Streamlit app for a car dealership. Customers rate their sales rep and leave a comment; an LLM (via Groq) labels each comment; the owner page shows what to coach reps on.

**Business question:** Which sales-rep behaviors should we coach on to raise customer ratings?

## Labels

Each label is a topic: what the comment is mainly about, whether it's good or bad. The star rating shows whether the customer was happy, so the owner page compares average stars across topics. The lowest-rated topics are the behaviors to coach on.

| Label | Definition |
|---|---|
| efficiency | How quickly and smoothly the visit went: wait times, paperwork, and getting the deal done. |
| pressure | Whether the rep pushed, rushed, or upsold the customer, or respected what they asked for. |
| honesty | Whether the rep was clear and truthful about price, fees, trade-in, financing, or the car's condition. |
| knowledge | How well the rep knew the car, its features, and the options available. |
| communication | How well the rep listened, replied to messages, followed up, and stayed easy to reach. |

If a comment mentions several topics, it gets the one the customer complains about most. A comment goes to manual review when it doesn't fit any topic (`unclear`, e.g. "Great guy!"), or when it has a label from an older version of the app.

On the owner page, each comment in the review list can be given the correct label or ignored. Either action takes it off the list. Ignored comments still count toward the average rating, but they're left out of the topic charts.

## Saving feedback

Streamlit Cloud deletes `feedback.csv` whenever the app restarts. To keep your feedback, open **Download or upload feedback** at the top of the owner page and download a CSV. Upload that file later to restore it, either adding it to the current feedback or replacing it. An uploaded CSV needs a `comment` column, a `rating` column, or both. Any comment without a valid label is labelled by the LLM when you import it.

## Run locally

1. Put your Groq key in `.streamlit/secrets.toml` (this file is git-ignored).
2. `pip install -r requirements.txt`
3. `streamlit run app.py`

## Deploy

On Streamlit Cloud, point the app at `app.py` in this repo and paste `GROQ_API_KEY = "..."` into **App settings → Secrets**.
