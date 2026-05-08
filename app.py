from datetime import date
import streamlit as st

st.set_page_config(
    page_title="ClinicFlow AI",
    page_icon="🏥",
    layout="centered"
)

st.title("🏥 ClinicFlow AI")
st.caption("Simple doctor-assisted appointment scheduling system.")


# -----------------------------
# System data
# -----------------------------

CLINICS = {
    "General Clinic": {
        "capacity": 100,
        "appointments": 85,
        "medicine": "Paracetamol",
        "stock": 300,
        "daily_demand": 40,
    },
    "Diabetes Clinic": {
        "capacity": 80,
        "appointments": 95,
        "medicine": "Insulin",
        "stock": 120,
        "daily_demand": 35,
    },
    "Cardiology Clinic": {
        "capacity": 70,
        "appointments": 60,
        "medicine": "Amlodipine",
        "stock": 180,
        "daily_demand": 25,
    },
    "Pediatrics Clinic": {
        "capacity": 90,
        "appointments": 75,
        "medicine": "Antibiotic Syrup",
        "stock": 90,
        "daily_demand": 20,
    },
}


# -----------------------------
# Functions
# -----------------------------

def get_congestion_level(appointments, capacity):
    ratio = appointments / capacity

    if ratio > 1:
        return "High"
    elif ratio >= 0.7:
        return "Medium"
    else:
        return "Low"


def get_stockout_risk(stock, daily_demand):
    if daily_demand == 0:
        return "Low", 999

    days_left = stock / daily_demand

    if days_left <= 3:
        return "Critical", days_left
    elif days_left <= 7:
        return "High", days_left
    elif days_left <= 14:
        return "Medium", days_left
    else:
        return "Low", days_left


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

    if score >= 60:
        level = "High"
    elif score >= 35:
        level = "Medium"
    else:
        level = "Low"

    return score, level


def suggest_appointment(priority, congestion):
    if priority == "High":
        return "Morning"
    elif congestion == "High":
        return "Afternoon"
    else:
        return "Next Available"


def analyze_patient(name, age, clinic_name, request_date, diabetes, hypertension):
    clinic = CLINICS[clinic_name]

    waiting_days = (date.today() - request_date).days

    congestion = get_congestion_level(
        clinic["appointments"],
        clinic["capacity"]
    )

    stockout_risk, days_left = get_stockout_risk(
        clinic["stock"],
        clinic["daily_demand"]
    )

    priority_score, priority = calculate_priority(
        age,
        diabetes,
        hypertension,
        waiting_days,
        congestion,
        stockout_risk
    )

    suggested_slot = suggest_appointment(priority, congestion)

    if stockout_risk in ["Critical", "High"]:
        medicine_note = "Medicine stock needs review."
    else:
        medicine_note = "Medicine stock is acceptable."

    return {
        "name": name,
        "clinic": clinic_name,
        "waiting_days": waiting_days,
        "priority": priority,
        "priority_score": priority_score,
        "suggested_slot": suggested_slot,
        "congestion": congestion,
        "medicine": clinic["medicine"],
        "stockout_risk": stockout_risk,
        "days_left": days_left,
        "medicine_note": medicine_note
    }


# -----------------------------
# Session state
# -----------------------------

if "result" not in st.session_state:
    st.session_state.result = None

if "final_slot" not in st.session_state:
    st.session_state.final_slot = None


# -----------------------------
# Patient form
# -----------------------------

with st.form("patient_form"):
    st.subheader("Patient Registration")

    name = st.text_input("Patient name", "Ahmed")
    age = st.number_input("Age", min_value=0, max_value=120, value=45)

    clinic_name = st.selectbox("Clinic", list(CLINICS.keys()))
    request_date = st.date_input("Request date", value=date.today())

    diabetes = st.selectbox("Diabetes", ["No", "Yes"])
    hypertension = st.selectbox("Hypertension", ["No", "Yes"])

    analyze_button = st.form_submit_button("Analyze Patient")

if analyze_button:
    st.session_state.result = analyze_patient(
        name,
        age,
        clinic_name,
        request_date,
        diabetes,
        hypertension
    )
    st.session_state.final_slot = None


# -----------------------------
# Results
# -----------------------------

if st.session_state.result:
    result = st.session_state.result

    st.subheader("System Suggestion")

    col1, col2 = st.columns(2)

    with col1:
        st.info(f"Priority: **{result['priority']}**")
        st.write(f"Priority score: {result['priority_score']}")
        st.write(f"Suggested appointment: **{result['suggested_slot']}**")

    with col2:
        st.write(f"Clinic congestion: **{result['congestion']}**")
        st.write(f"Medicine: **{result['medicine']}**")
        st.write(f"Stockout risk: **{result['stockout_risk']}**")
        st.write(f"Days left: {result['days_left']:.1f}")

    st.warning(result["medicine_note"])

    st.subheader("Doctor Decision")

    decision = st.radio(
        "Choose final decision",
        ["Approve suggested appointment", "Modify appointment", "Needs review"]
    )

    if decision == "Approve suggested appointment":
        st.session_state.final_slot = result["suggested_slot"]

    elif decision == "Modify appointment":
        st.session_state.final_slot = st.selectbox(
            "Choose new appointment",
            ["Morning", "Afternoon", "Evening", "Next Available Day"]
        )

    else:
        st.session_state.final_slot = "Pending Review"

    if st.button("Confirm Decision"):
        st.success("Decision confirmed.")

        st.write(f"Patient: **{result['name']}**")
        st.write(f"Clinic: **{result['clinic']}**")
        st.write(f"Final appointment: **{st.session_state.final_slot}**")
        st.write(f"Doctor decision: **{decision}**")