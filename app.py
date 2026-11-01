import os
from datetime import datetime

import altair as alt
import pandas as pd
import requests
import streamlit as st

# Business: a car dealership.
# Question: Which sales-rep behaviors should we coach on to raise customer ratings?

KEY = st.secrets["GROQ_API_KEY"]
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"   # check Groq's current free models here: https://console.groq.com/docs/rate-limits

DATA_FILE = "feedback.csv"
# status is "" until the owner reviews a comment, then "reviewed" or "ignored".
COLUMNS = ["timestamp", "rep", "rating", "comment", "label", "status"]

REPS = ["Alex", "Jordan", "Sam", "Taylor"]

# Labels are topics: what the comment is mainly about, good or bad.
# The star rating shows whether the customer was happy with it.
LABELS = {
    "efficiency": "How quickly and smoothly the visit went: wait times, paperwork, and getting the deal done.",
    "pressure": "Whether the rep pushed, rushed, or upsold the customer, or respected what they asked for.",
    "honesty": "Whether the rep was clear and truthful about price, fees, trade-in, financing, or the car's condition.",
    "knowledge": "How well the rep knew the car, its features, and the options available.",
    "communication": "How well the rep listened, replied to messages, followed up, and stayed easy to reach.",
}
ALLOWED = list(LABELS)


def label_comment(text):
    definitions = "\n".join(f"- {name}: {desc}" for name, desc in LABELS.items())
    prompt = (
        "You label customer comments about sales reps at a car dealership.\n"
        "Label the comment by the topic it is mainly about, whether the comment is positive or negative.\n"
        f"Reply with exactly one word from this list: {', '.join(ALLOWED)}.\n\n"
        f"Definitions:\n{definitions}\n\n"
        "If it mentions several topics, pick the one the customer complains about most.\n"
        "If it doesn't fit any topic, reply: unclear\n"
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
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(DATA_FILE)
    if "status" not in df.columns:
        df["status"] = ""
    df["status"] = df["status"].fillna("")
    return df


def save_data(df):
    df[COLUMNS].to_csv(DATA_FILE, index=False)


def save_row(row):
    save_data(pd.concat([load_data(), pd.DataFrame([row])], ignore_index=True))


def resolve_review(index, choice):
    df = load_data()
    if choice == "ignore":
        df.loc[index, "status"] = "ignored"
    else:
        df.loc[index, "label"] = choice
        df.loc[index, "status"] = "reviewed"
    save_data(df)


def needs_review(row):
    # The owner already handled it.
    if row["status"] in ("reviewed", "ignored"):
        return False
    # The comment isn't one of the topics: "unclear", or a label from an older version of the app.
    return row["label"] not in ALLOWED and row["label"] != "no comment"


def clean_upload(df):
    # Needs a comment or rating column; any other missing columns are filled in.
    df.columns = [c.strip().lower() for c in df.columns]
    if "comment" not in df.columns and "rating" not in df.columns:
        raise ValueError("The CSV needs a 'comment' column, a 'rating' column, or both.")
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df["comment"] = df["comment"].fillna("").astype(str).str.strip()
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["rep"] = df["rep"].fillna("").replace("", "Unknown")
    df["status"] = df["status"].fillna("")
    df["label"] = df["label"].fillna("").astype(str).str.strip().str.lower()
    df = df[(df["comment"] != "") | df["rating"].notna()].reset_index(drop=True)

    # Label any comment that doesn't already have a valid label.
    known = ALLOWED + ["unclear", "no comment"]
    for i, row in df.iterrows():
        if row["comment"] == "":
            df.loc[i, "label"] = "no comment"
        elif row["label"] not in known:
            df.loc[i, "label"] = label_comment(row["comment"])
    return df[COLUMNS]


def data_tools(df):
    with st.expander("Download or upload feedback"):
        st.download_button(
            "Download feedback as CSV",
            df[COLUMNS].to_csv(index=False),
            file_name="feedback.csv",
            mime="text/csv",
            disabled=df.empty,
        )

        st.divider()
        upload = st.file_uploader("Upload a feedback CSV", type="csv")
        mode = st.radio("What should the upload do?",
                        ["Add to current feedback", "Replace current feedback"])
        st.caption("Comments without a label are labelled by the LLM when you import.")
        if upload is not None and st.button("Import"):
            try:
                with st.spinner("Importing..."):
                    new = clean_upload(pd.read_csv(upload))
            except Exception as e:
                st.error(f"Couldn't import that file: {e}")
                return
            if mode == "Add to current feedback":
                new = pd.concat([df, new], ignore_index=True)
            save_data(new)
            st.rerun()


def customer_page():
    st.title("Rate your sales rep")
    st.write("Tell us how your visit went. Leave a star rating, a comment, or both — at least one is required.")

    with st.form("feedback", clear_on_submit=True):
        rep = st.selectbox("Who helped you?", REPS)
        st.markdown("Star rating")
        stars = st.feedback("stars")
        comment = st.text_area("Comment")
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
                "status": "",
            })
        st.success("Thanks for your feedback!")


def topic_chart(data, value, title, scale, axis):
    # Horizontal bars so topic names stay readable, always in the same order.
    return alt.Chart(data).mark_bar().encode(
        x=alt.X(f"{value}:Q", title=title, scale=scale, axis=axis),
        y=alt.Y("label:N", title=None, sort=ALLOWED),
        tooltip=["label", value],
    )


def owner_page():
    st.title("Sales rep coaching dashboard")
    st.caption("Which sales-rep behaviors should we coach on to raise customer ratings?")

    df = load_data()
    data_tools(df)
    if df.empty:
        st.info("No feedback yet.")
        return

    df["needs_review"] = df.apply(needs_review, axis=1)
    review = df[df["needs_review"]]
    # Ignored comments still count toward the average rating, but not the topic charts.
    topics = df[df["label"].isin(ALLOWED) & (df["status"] != "ignored")]
    stars = topics.dropna(subset=["rating"]).groupby("label")["rating"].mean().round(1)

    col1, col2, col3 = st.columns(3)
    col1.metric("Average rating", f"{df['rating'].mean():.1f} ★" if df["rating"].notna().any() else "–")
    if stars.empty:
        col2.metric("Lowest-rated topic", "–")
    else:
        col2.metric("Lowest-rated topic", stars.idxmin(), f"{stars.min():.1f} ★ average",
                    delta_color="off", delta_arrow="off")
    col3.metric("Need manual review", len(review))

    st.subheader("What customers talk about")
    counts = topics["label"].value_counts().reindex(ALLOWED, fill_value=0).rename_axis("label").reset_index(name="count")
    st.altair_chart(topic_chart(counts, "count", "Comments", alt.Scale(domainMin=0),
                                alt.Axis(tickMinStep=1, format="d")))

    st.subheader("Average stars by topic")
    st.caption("Low bars are the behaviors to coach on.")
    if stars.empty:
        st.write("No rated comments yet.")
    else:
        st.altair_chart(topic_chart(stars.reset_index(name="stars"), "stars", "Average stars",
                                    alt.Scale(domain=[0, 5]), alt.Axis(values=[0, 1, 2, 3, 4, 5])))

    st.subheader("Comments that need manual review")
    if review.empty:
        st.write("Nothing to review.")
    options = ALLOWED + ["ignore"]
    for i, row in review.iterrows():
        with st.container(border=True):
            rating = f"{int(row['rating'])} ★" if pd.notna(row["rating"]) else "no rating"
            st.markdown(f"**{row['rep']}** · {rating} · label: `{row['label']}` · {row['timestamp']}")
            st.write(row["comment"] if pd.notna(row["comment"]) else "")
            pick, button = st.columns([3, 1], vertical_alignment="bottom")
            default = options.index(row["label"]) if row["label"] in options else 0
            choice = pick.selectbox("Set label", options, index=default, key=f"choice_{i}")
            if button.button("Save", key=f"save_{i}"):
                resolve_review(i, choice)
                st.rerun()

    with st.expander("Label definitions"):
        for name, desc in LABELS.items():
            st.markdown(f"- **{name}**: {desc}")


page = st.sidebar.radio("Page", ["Customer", "Owner"])
if page == "Customer":
    customer_page()
else:
    owner_page()
