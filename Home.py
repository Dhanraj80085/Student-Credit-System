import streamlit as st
import numpy as np
from PIL import Image
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image
import datetime

# ----------------------------
# MongoDB Connection
# ----------------------------
uri = "mongodb+srv://ngodse8008:xQE4yFXgSuQpFyrn@cluster0.g2vidpo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    mongo_status = True
    st.success("✅ Connected to MongoDB!")
except Exception as e:
    st.error(f"❌ MongoDB connection error: {e}")
    mongo_status = False

db = client["weekly_reports"]
collection = db["student_submissions"]

# ----------------------------
# Auto-delete all data on Monday
# ----------------------------
today_name = datetime.datetime.now().strftime("%A")
if today_name == "Monday" and mongo_status:
  print(f"⚠️ All data erased (Monday cleanup).")
# ----------------------------
# Load ResNet50 Model
# ----------------------------
@st.cache_resource
def load_resnet():
    with st.spinner("Loading AI model for image verification..."):
        model = ResNet50(weights='imagenet')
    return model

resnet_model = load_resnet()

# ----------------------------
# Streamlit App Layout
# ----------------------------
st.set_page_config(page_title="Weekly Study Report", page_icon="📝", layout="centered")

st.title("📝 Weekly Study Report")
st.write("Please fill in your child’s study details for this week.")

st.markdown("---")

# --- Student Info ---
st.header("👤 Student Information")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Child’s Name")
    std = st.selectbox("Class", ["Nursery", "LKG", "UKG"])
with col2:
    gender = st.radio("Gender", ["Male", "Female"])

st.markdown("---")

# --- Study Hours ---
st.header("📚 Weekly Study Hours")
st.write("Enter study hours (max 2/day).")
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
study_hours = {}
cols = st.columns(3)
for idx, day in enumerate(days):
    with cols[idx % 3]:
        study_hours[day] = st.number_input(f"{day}", min_value=0, max_value=2, step=1, key=day)

st.markdown("---")

# --- Extra Activity ---
st.header("🏃‍♂️ Extra Activities (Optional)")
extra_activity = st.checkbox("Did your child do any extra activities?")

activity_image = None
activity_type = None
activity_intensity = None
activity_credit = 0
verified_as_activity = False

activity_keywords = {
    "Outdoor Exercise": [
        "running", "jogging", "bicycle", "cycling", "scooter", "skateboard", "track", "trail", "sprinting",
        "sprinter", "sportswear", "tennis shoes", "tennis_shoe", "sneakers", "sneaker", "helmet", "sunlight",
        "trees", "tree", "sunshade", "grass", "outdoor", "sunshade", "backyard", "field", "park", "climbing frame",
        "swing", "slide", "seesaw", "sandbox", "playground", "jungle gym", "monkey bars", "balance beam", "racing",
        "tag", "hide and seek", "catch", "hopscotch", "climbing_frame", "monkey_bar", "jungle_gym"
    ],
    "Indoor Activity": [
        "reading", "storybook", "storybook illustrations", "bookshelf", "bookshop", "study table", "notebook",
        "floor mat", "indoor", "indoor swing", "lego", "building blocks", "construction toy", "doll", "dollhouse",
        "toy car", "action figure", "teddy bear", "plushie", "plush", "indoor ball", "foam blocks", "tent",
        "indoor tunnel", "magnetic tiles", "rainy day", "couch", "lamp", "kids table", "indoor setup",
        "quiet play", "toy kitchen", "mini tools", "train set", "train_set", "busy board", "quiet book",
        "bouncy castle", "book", "story", "toyshop", "pencil_box"
    ],
    "Sports": [
        "soccer", "football", "basketball", "cricket", "tennis", "badminton", "baseball", "volleyball",
        "golf", "table tennis", "ping pong", "ping-pong_ball", "net", "bat", "ball", "jersey", "sports shoes",
        "sportswear", "sports", "coach", "team match", "scoreboard", "sports court", "stadium", "goalpost",
        "referee", "trophy", "tennis racket", "sports bag", "glove", "kick", "pass", "dribble", "catch", "serve",
        "tournament", "sports field", "cones", "whistle", "soccer_ball", "cricket_ball", "baseball", "football_helmet",
        "table_tennis", "race", "racket", "running_shoe", "sports_car"
    ],
    "Gardening": [
        "plant", "watering can", "soil", "flowerpot", "terracotta pot", "greenhouse", "sapling", "mulch",
        "compost", "shovel", "hoe", "rake", "trowel", "watering", "seedling", "gloves", "sunhat", "sun_hat",
        "potted herb", "rose", "daisy", "cactus", "sprinkler", "garden bed", "vegetable patch", "vegetable",
        "terrace garden", "insect", "butterfly", "ladybug", "bee", "green leaves", "garden fence", "sprout",
        "raised bed", "lawn mower", "plant markers", "potted_plant", "tree", "flower", "knee pad", "gardening"
    ],
    "Cooking/Baking": [
        "cooking", "baking", "frying", "stirring", "rolling pin", "rolling_pin", "whisk", "measuring cup",
        "measuring_cup", "muffin tin", "cookie cutter", "mixing bowl", "batter", "apron", "chef hat",
        "kitchen", "countertop", "gas stove", "electric stove", "oven", "microwave", "pan", "pot", "frying_pan",
        "chopping board", "knife", "ladle", "ingredients", "egg", "flour", "dough", "sugar", "spoon",
        "kitchen towel", "cutlery", "table setting", "bakeware", "sprinkles", "decorating", "cupcake",
        "pancake", "syrup", "tongs", "sifter", "play kitchen", "pretend chef", "mixer", "toaster", "blender",
        "cutting_board", "spatula", "baking_pan", "chef_hat"
    ],
    "Board Games": [
        "chess", "chessboard", "pawn", "rook", "queen", "king", "carrom", "ludo", "dice", "tokens",
        "snakes and ladders", "board game", "board_game", "scrabble", "domino", "tiles", "word game",
        "connect four", "checkers", "game board", "score sheet", "rule book", "card deck", "joker",
        "playing cards", "monopoly", "trading cards", "card holder", "spinner", "turn-based", "tabletop",
        "strategy", "roll", "game night", "kid-friendly game"
    ],
    "Arts & Crafts": [
        "drawing", "coloring", "painting", "crayons", "watercolor", "sketching", "stamping", "markers",
        "colored pencils", "scissors", "glue stick", "glue", "glitter", "origami", "folded paper", "craft paper",
        "pipe cleaner", "googly eyes", "paper plate", "canvas", "poster", "paintbrush", "acrylic", "chart",
        "scrapbook", "beads", "string", "yarn", "knitting", "sticker", "pop stick", "tape", "pom poms",
        "scrap art", "handmade card", "DIY kit", "foam shapes", "hole punch", "cutout", "glue gun", "stencil",
        "ink", "calligraphy", "art display", "kids easel", "finger painting", "paint", "chalkboard", "whiteboard",
        "coloring_book", "marker", "crayon", "palette", "stickers", "paper"
    ],
    "Other": []
}

if extra_activity:
    activity_type = st.selectbox("Activity Type", list(activity_keywords.keys()))
    activity_intensity = st.radio("Activity Intensity", ["Low", "Medium", "High"])
    activity_image = st.file_uploader("Upload Activity Image", type=["jpg", "jpeg", "png"])

    manual_override = False
    type_matched = False
    top_confidence = 0

    if activity_image is not None:
        img = Image.open(activity_image).convert('RGB')
        st.image(img, caption="Uploaded Image", use_container_width=True)

        img_resized = img.resize((224, 224))
        img_array = image.img_to_array(img_resized)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        preds = resnet_model.predict(img_array)
        decoded_preds = decode_predictions(preds, top=3)[0]

        st.write("**Image Predictions:**")
        for i, (imagenetID, label, prob) in enumerate(decoded_preds):
            st.write(f"{i+1}. {label} ({prob*100:.2f}%)")

        selected_keywords = activity_keywords.get(activity_type, [])
        top_labels = [label.lower() for (_, label, _) in decoded_preds]
        top_confidence = decoded_preds[0][2]

        activity_verified = top_confidence >= 0.5
        category_matched = any(any(kw in label for kw in selected_keywords) for label in top_labels)

        if activity_verified:
            verified_as_activity = True
            if category_matched:
                type_matched = True
                st.success(f"✅ Image verified as a **{activity_type}** activity.")
            else:
                st.warning("⚠️ Activity verified, but doesn't match selected category.")
                manual_override = st.checkbox("✅ Manually confirm relevance")
                if manual_override:
                    type_matched = True
                    st.info("Manual confirmation accepted.")
        else:
            st.error("❌ Could not verify image as valid activity.")

    if type_matched:
        activity_credit = {"Low": 5, "Medium": 10, "High": 15}.get(activity_intensity, 0)

st.markdown("---")

# --- Calculate Credits ---
total_hours = sum(study_hours.values())
study_credit = sum([20 if hrs > 1 else 10 for hrs in study_hours.values()])
total_credit = study_credit + activity_credit

# --- Final Submit ---
if st.button("✅ Submit Weekly Report"):
    st.subheader("📊 Report Summary")

    if not name:
        st.warning("Please enter your child’s name.")
    else:
        if total_hours < 8:
            st.error(f"{name} may need more study time. Total: **{total_hours} hrs**.")
        else:
            st.success(f"Great job! {name} studied **{total_hours} hrs** this week.")

        st.info(f"**Credits Earned:** {total_credit} points")
        st.caption(f"Includes {study_credit} (study) + {activity_credit} (activities)")

        with st.expander("See Full Report Details"):
            st.write(f"**Name:** {name}")
            st.write(f"**Class:** {std}")
            st.write(f"**Gender:** {gender}")
            st.write("**Study Hours:**")
            for day in days:
                st.write(f"- {day}: {study_hours[day]} hrs")

            if extra_activity:
                st.write(f"**Activity:** {activity_type}")
                st.write(f"**Intensity:** {activity_intensity}")
                st.write(f"**Activity Credits:** {activity_credit}")
                if activity_image:
                    st.image(activity_image, caption=f"{activity_type}", use_container_width=True)

        # --- Save to MongoDB ---
        if mongo_status:
            submission = {
                "name": name,
                "class": std,
                "gender": gender,
                "study_hours": study_hours,
                "total_study_hours": total_hours,
                "study_credit": study_credit,
                "extra_activity": {
                    "type": activity_type,
                    "intensity": activity_intensity,
                    "credit": activity_credit,
                    "verified": type_matched,
                } if extra_activity else None,
                "total_credit": total_credit
            }

            try:
                collection.insert_one(submission)
                st.success("📁 Report successfully saved to MongoDB!")
            except Exception as e:
                st.error(f"Failed to save to database: {e}")

