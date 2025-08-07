import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# ----------------------------
# Page Config & Custom CSS
# ----------------------------
st.set_page_config(page_title="🏆 Top Performers", layout="centered")

# Minimalist CSS
st.markdown("""
    <style>
    .main {
        background-color: #f9f9f9;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1 {
        text-align: center;
        font-size: 2.5rem;
        color: #333333;
    }
    .stTable tbody tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------
# Title
# ----------------------------
st.markdown("<h1>🏆 Weekly Top 7 Student Performers</h1>", unsafe_allow_html=True)

# ----------------------------
# MongoDB Connection
# ----------------------------
uri = "mongodb+srv://ngodse8008:xQE4yFXgSuQpFyrn@cluster0.g2vidpo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    db = client["weekly_reports"]
    collection = db["student_submissions"]
except Exception as e:
    st.error(f"❌ Could not connect to MongoDB: {e}")
    st.stop()

# ----------------------------
# Fetch Verified Submissions
# ----------------------------
query = {
    "extra_activity.verified": True
}

records = list(collection.find(query))

if not records:
    st.warning("No verified activity data found.")
    st.stop()

# ----------------------------
# Prepare DataFrame
# ----------------------------
df = pd.DataFrame(records)
df = df[["name", "class", "total_credit", "study_credit"]]
df = df.dropna(subset=["total_credit"])
df = df.sort_values(by="total_credit", ascending=False).reset_index(drop=True)
df["Rank"] = df.index + 1

# Top 7
top7 = df.head(7)

# ----------------------------
# Top 3 Metrics
# ----------------------------
top3 = top7.head(3)
cols = st.columns(3)
for i, row in top3.iterrows():
    with cols[i]:
        st.metric(
            label=f"🥇 {row['name']} ({row['class']})",
            value=f"{row['total_credit']} pts",
            delta=f"Study: {row['study_credit']}"
        )

# ----------------------------
# Leaderboard Table
# ----------------------------
st.subheader("📋 Full Leaderboard (Top 7)")
st.dataframe(
    top7[["Rank", "name", "class", "total_credit", "study_credit"]],
    use_container_width=True,
    height=350
)
