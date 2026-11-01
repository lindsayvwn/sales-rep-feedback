import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# Business: a car dealership.
# Question: Which sales-rep behaviors should we coach on to raise customer ratings?

KEY = st.secrets["GROQ_API_KEY"]
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"   # check Groq's current free models here: https://console.groq.com/docs/rate-limits

DATA_FILE = "feedback.csv"
COLUMNS = ["timestamp", "rep", "rating", "comment", "label"]

REPS = ["Alex", "Jordan", "Sam", "Taylor"]

# One line per label: what the comment is mainly about.
LABELS = {
    "helpful": "The rep was knowledgeable, friendly, or helped the customer find the right car.",
    "pushy": "The rep used high-pressure tactics, rushed the customer, or pushed add-ons they didn't want.",
    "communication": "The rep was slow to respond, didn't follow up, didn't listen, or was hard to reach.",
    "pricing": "The rep was unclear or misleading about price, fees, trade-in value, or financing.",
}
ALLOWED = list(LABELS)
NEGATIVE = ["pushy", "communication", "pricing"]


def label_comment(text):
    definitions = "\n".join(f"- {name}: {desc}" for name, desc in LABELS.items())
    prompt = (
        "You label customer comments about sales reps at a car dealership.\n"
        f"Label the comment with exactly one word from this list: {', '.join(ALLOWED)}.\n\n"
        f"Definitions:\n{definitions}\n\n"
        "If it has praise and a complaint, label by the bigger problem.\n"
        "Sarcasm counts as a complaint.\n"
        "Reply with the one word only.\n\n"
        f"Comment: {text}"
    )
    try:
        response = requests.post(
            URL,
            headers={"Authorization": f"Bearer {KEY}"},
            json={"model": MODEL, "temperature": 0,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        answer = response.json()["choices"][0]["message"]["content"]
    except Exception:
        return "unclear"
    label = answer.strip().strip(".").lower()
    return label if label in ALLOWED else "unclear"


def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=COLUMNS)


def save_row(row):
    df = pd.concat([load_data(), pd.DataFrame([row])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)


def needs_review(row):
    # The model didn't return an allowed label.
    if row["label"] == "unclear":
        return True
    # The star rating and the label disagree.
    if pd.notna(row["rating"]):
        if row["label"] == "helpful" and row["rating"] <= 2:
            return True
        if row["label"] in NEGATIVE and row["rating"] == 5:
            return True
    return False


def customer_page():
    st.title("Rate your sales rep")
    st.write("Tell us how your visit went. Leave a star rating, a comment, or both.")

    with st.form("feedback", clear_on_submit=True):
        rep = st.selectbox("Who helped you?", REPS)
        stars = st.feedback("stars")
        comment = st.text_area("Comments (optional)")
        submitted = st.form_submit_button("Submit")

    if submitted:
        rating = stars + 1 if stars is not None else None
        comment = comment.strip()
        if rating is None and not comment:
            st.error("Please leave a star rating, a comment, or both.")
            return
        with st.spinner("Saving your feedback..."):
            label = label_comment(comment) if comment else "no comment"
            save_row({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "rep": rep,
                "rating": rating,
                "comment": comment,
                "label": label,
            })
        st.success("Thanks for your feedback!")


def owner_page():
    st.title("Sales rep coaching dashboard")
    st.caption("Which sales-rep behaviors should we coach on to raise customer ratings?")

    df = load_data()
    if df.empty:
        st.info("No feedback yet.")
        return

    df["needs_review"] = df.apply(needs_review, axis=1)
    comments = df[df["label"] != "no comment"]
    complaints = comments[comments["label"].isin(NEGATIVE)]
    review = df[df["needs_review"]]

    col1, col2, col3 = st.columns(3)
    col1.metric("Average rating", f"{df['rating'].mean():.1f} ★" if df["rating"].notna().any() else "–")
    col2.metric("Top complaint", complaints["label"].mode()[0] if not complaints.empty else "–")
    col3.metric("Need manual review", len(review))

    st.subheader("What customers talk about")
    st.bar_chart(comments["label"].value_counts())

    st.subheader("Complaints by rep")
    if complaints.empty:
        st.write("No complaints yet.")
    else:
        st.bar_chart(pd.crosstab(complaints["rep"], complaints["label"]))

    st.subheader("Comments that need manual review")
    if review.empty:
        st.write("Nothing to review.")
    for _, row in review.iterrows():
        with st.container(border=True):
            rating = f"{int(row['rating'])} ★" if pd.notna(row["rating"]) else "no rating"
            st.markdown(f"**{row['rep']}** · {rating} · label: `{row['label']}` · {row['timestamp']}")
            st.write(row["comment"] if pd.notna(row["comment"]) else "")

    with st.expander("Label definitions"):
        for name, desc in LABELS.items():
            st.markdown(f"- **{name}**: {desc}")


page = st.sidebar.radio("Page", ["Customer", "Owner"])
if page == "Customer":
    customer_page()
else:
    owner_page()
