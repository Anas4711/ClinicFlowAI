from datetime import date, datetime

import joblib
import pandas as pd
import streamlit as st


# -----------------------------
# Page setup
# -----------------------------

st.set_page_config(
    page_title="ClinicFlow AI",
    page_icon="🏥",
    layout="centered"
)

st.title("🏥 ClinicFlow AI")
st.caption("ML-based doctor-assisted appointment scheduling system.")


# -----------------------------
# Load trained models
# -----------------------------

congestion_model = joblib.load("models/congestion_model.pkl")
congestion_scaler = joblib.load("models/congestion_scaler.pkl")
congestion_features = joblib.load("models/congestion_features.pkl")

stockout_model = joblib.load("models/stockout_model.pkl")
stockout_scaler = joblib.load("models/stockout_scaler.pkl")
stockout_features = joblib.load("models/stockout_features.pkl")


# -----------------------------
# Clinic system data
# -----------------------------

CLINICS = {
    "General Clinic": {
        "avg_age": 40,
        "diabetes_count": 20,
        "hypertension_count": 25,
        "sms_received_count": 50,
        "medicine_type": "n02be",
        "medicine": "Paracetamol",
        "stock": 300,
        "daily_demand": 40,
    },
    "Diabetes Clinic": {
        "avg_age": 55,
        "diabetes_count": 60,
        "hypertension_count": 35,
        "sms_received_count": 70,
        "medicine_type": "m01ab",
        "medicine": "Insulin",
        "stock": 120,
        "daily_demand": 35,
    },
    "Cardiology Clinic": {
        "avg_age": 60,
        "diabetes_count": 25,
        "hypertension_count": 55,
        "sms_received_count": 45,
        "medicine_type": "r03",
        "medicine": "Amlodipine",
        "stock": 180,
        "daily_demand": 25,
    },
    "Pediatrics Clinic": {
        "avg_age": 12,
        "diabetes_count": 5,
        "hypertension_count": 3,
        "sms_received_count": 40,
        "medicine_type": "r06",
        "medicine": "Antibiotic Syrup",
        "stock": 90,
        "daily_demand": 20,
    },
}


# -----------------------------
# Helper functions
# -----------------------------

def predict_congestion(clinic, request_date, waiting_days):
    input_df = pd.DataFrame([{
        "avg_age": clinic["avg_age"],
        "diabetes_count": clinic["diabetes_count"],
        "hypertension_count": clinic["hypertension_count"],
        "sms_received_count": clinic["sms_received_count"],
        "avg_waiting_days": waiting_days,
        "appointment_day_of_week": request_date.weekday(),
        "appointment_month": request_date.month,
    }])

    input_df = input_df[congestion_features]
    input_scaled = congestion_scaler.transform(input_df)

    return congestion_model.predict(input_scaled)[0]


def predict_stockout(clinic, request_date):
    weekday_name = request_date.strftime("%A")
    medicine_type = clinic["medicine_type"]

    input_df = pd.DataFrame([{
        "year": request_date.year,
        "month": request_date.month,
        "hour": 276,
        "daily_demand": clinic["daily_demand"],
        "current_stock": clinic["stock"],

        "weekday_name_Monday": weekday_name == "Monday",
        "weekday_name_Saturday": weekday_name == "Saturday",
        "weekday_name_Sunday": weekday_name == "Sunday",
        "weekday_name_Thursday": weekday_name == "Thursday",
        "weekday_name_Tuesday": weekday_name == "Tuesday",
        "weekday_name_Wednesday": weekday_name == "Wednesday",

        "medicine_type_m01ae": medicine_type == "m01ae",
        "medicine_type_n02ba": medicine_type == "n02ba",
        "medicine_type_n02be": medicine_type == "n02be",
        "medicine_type_n05b": medicine_type == "n05b",
        "medicine_type_n05c": medicine_type == "n05c",
        "medicine_type_r03": medicine_type == "r03",
        "medicine_type_r06": medicine_type == "r06",
    }])

    input_df = input_df.reindex(columns=stockout_features, fill_value=False)
    input_scaled = stockout_scaler.transform(input_df)

    return stockout_model.predict(input_scaled)[0]


def calculate_priority(age, diabetes, hypertension, waiting_days, congestion, stockout_risk):
    score = 0

    if age >= 65:
        score += 20

    if diabetes == "Yes":
        score += 15

    if hypertension == "Yes":
        score += 15

    if waiting_days >= 14:
        score += 20
    elif waiting_days >= 7:
        score += 10

    if congestion == "High":
        score += 15
    elif congestion == "Medium":
        score += 8

    if stockout_risk in ["Critical", "High"]:
        score += 15
    elif stockout_risk == "Medium":
        score += 8

    if score >= 60:
        level = "High"
    elif score >= 35:
        level = "Medium"
    else:
        level = "Low"

    return score, level


def get_urgency_description(priority):
    if priority == "High":
        return "High urgency: this patient should be scheduled as early as possible."
    elif priority == "Medium":
        return "Medium urgency: this patient should be scheduled soon, but not necessarily first."
    else:
        return "Low urgency: this patient can be scheduled normally."


def suggest_appointment(priority, congestion):
    if priority == "High":
        return "Morning"
    elif congestion == "High":
        return "Afternoon"
    else:
        return "Next Available"


def get_recommendation(priority, congestion, stockout_risk):
    if priority == "High":
        recommendation = "Give this patient an earlier appointment."
    elif congestion == "High":
        recommendation = "Move this patient to a less crowded time if possible."
    else:
        recommendation = "Schedule normally."

    if stockout_risk in ["Critical", "High"]:
        recommendation += " Pharmacy should review medicine stock."

    return recommendation


def get_priority_rank(priority):
    if priority == "High":
        return 3
    elif priority == "Medium":
        return 2
    else:
        return 1


def sort_queue_fairly(queue):
    queue_df = pd.DataFrame(queue)

    queue_df = queue_df.sort_values(
        by=["Priority Rank", "Waiting Days", "Registration Order"],
        ascending=[False, False, True]
    )

    return queue_df.drop(columns=["Priority Rank", "Registration Order"])


# -----------------------------
# Session state
# -----------------------------

if "result" not in st.session_state:
    st.session_state.result = None

if "final_result" not in st.session_state:
    st.session_state.final_result = None

if "appointment_queue" not in st.session_state:
    st.session_state.appointment_queue = []

if "registration_counter" not in st.session_state:
    st.session_state.registration_counter = 0


# -----------------------------
# Patient form
# -----------------------------

with st.form("patient_form"):
    st.subheader("Patient Registration")

    patient_name = st.text_input("Patient name", "Ahmed")
    age = st.number_input("Age", min_value=0, max_value=120, value=45)

    clinic_name = st.selectbox("Clinic", list(CLINICS.keys()))
    request_date = st.date_input("Request date", value=date.today())

    diabetes = st.selectbox("Diabetes", ["No", "Yes"])
    hypertension = st.selectbox("Hypertension", ["No", "Yes"])

    analyze_button = st.form_submit_button("Analyze Patient")

if analyze_button:
    clinic = CLINICS[clinic_name]
    waiting_days = max((date.today() - request_date).days, 0)

    congestion = predict_congestion(clinic, request_date, waiting_days)
    stockout_risk = predict_stockout(clinic, request_date)

    priority_score, priority = calculate_priority(
        age,
        diabetes,
        hypertension,
        waiting_days,
        congestion,
        stockout_risk
    )

    suggested_slot = suggest_appointment(priority, congestion)
    recommendation = get_recommendation(priority, congestion, stockout_risk)
    urgency_description = get_urgency_description(priority)

    st.session_state.result = {
        "patient_name": patient_name,
        "age": age,
        "clinic_name": clinic_name,
        "medicine": clinic["medicine"],
        "stock": clinic["stock"],
        "daily_demand": clinic["daily_demand"],
        "request_date": request_date,
        "waiting_days": waiting_days,
        "congestion": congestion,
        "stockout_risk": stockout_risk,
        "priority": priority,
        "priority_score": priority_score,
        "urgency_description": urgency_description,
        "suggested_slot": suggested_slot,
        "recommendation": recommendation,
    }

    st.session_state.final_result = None


# -----------------------------
# System results
# -----------------------------

if st.session_state.result:
    result = st.session_state.result

    st.subheader("System Suggestion")

    st.info(f"Patient urgency: **{result['priority']}**")
    st.caption(result["urgency_description"])

    st.write(f"Waiting days: **{result['waiting_days']}**")
    st.write(f"Suggested appointment: **{result['suggested_slot']}**")
    st.write(f"Clinic congestion prediction: **{result['congestion']}**")
    st.write(f"Medication stockout prediction: **{result['stockout_risk']}**")
    st.write(f"Medicine: **{result['medicine']}**")
    st.write(f"Current stock: **{result['stock']}**")

    st.warning(result["recommendation"])

    st.subheader("Doctor Final Decision")

    decision = st.radio(
        "Doctor decision",
        ["Approve", "Modify", "Needs review"]
    )

    if decision == "Approve":
        final_slot = result["suggested_slot"]

    elif decision == "Modify":
        final_slot = st.selectbox(
            "Choose new appointment",
            ["Morning", "Afternoon", "Evening", "Next Available Day"]
        )

    else:
        final_slot = "Pending Review"

    if st.button("Confirm Decision"):
        st.session_state.registration_counter += 1

        final_record = {
            "Patient": result["patient_name"],
            "Age": result["age"],
            "Clinic": result["clinic_name"],
            "Urgency": result["priority"],
            "Waiting Days": result["waiting_days"],
            "Final Appointment": final_slot,
            "Doctor Decision": decision,
            "Clinic Congestion": result["congestion"],
            "Medicine Risk": result["stockout_risk"],
            "Medicine": result["medicine"],
            "Priority Rank": get_priority_rank(result["priority"]),
            "Registration Order": st.session_state.registration_counter,
            "Registered At": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        st.session_state.appointment_queue.append(final_record)
        st.session_state.final_result = final_record


# -----------------------------
# Appointment queue
# -----------------------------

if st.session_state.appointment_queue:
    st.subheader("Appointment Queue")

    st.caption(
        "Queue is sorted fairly by urgency first, then by waiting days, then by registration order."
    )

    queue_df = sort_queue_fairly(st.session_state.appointment_queue)

    st.dataframe(queue_df, use_container_width=True)

    if st.button("Clear Queue"):
        st.session_state.appointment_queue = []
        st.session_state.final_result = None
        st.success("Queue cleared.")


# -----------------------------
# Final output
# -----------------------------

if st.session_state.final_result:
    final = st.session_state.final_result

    st.success("Decision confirmed and patient added to the appointment queue.")

    st.write(f"Patient: **{final['Patient']}**")
    st.write(f"Clinic: **{final['Clinic']}**")
    st.write(f"Final appointment: **{final['Final Appointment']}**")
    st.write(f"Doctor decision: **{final['Doctor Decision']}**")