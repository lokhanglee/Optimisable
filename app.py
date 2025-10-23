import os
import re
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import optimiser  # your Gurobi logic file

# -----------------------------
# Utility functions (AI command)
# -----------------------------

def extract_json_object(text: str):
    """Extract and parse the first top-level JSON object from text."""
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    end = None
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return None
    candidate = text[start:end]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        fixed = candidate.replace("'", '"')
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None


FIELD_ALIASES = {
    "cost": "Staff Cost",
    "staff cost": "Staff Cost",
    "min days": "Min Working Days per Week",
    "max days": "Max Working Days per Week",
}

def normalize_field_name(raw: str) -> str:
    key = raw.strip().lower()
    return FIELD_ALIASES.get(key, raw)


def fallback_parse_command(text: str):
    """Parse simple imperative commands when LLM output fails."""
    t = text.strip()

    # Set Staff X cost to N
    m = re.match(r"set\s+(staff\s+\d+)\s+([a-z\s]+)\s+to\s+(-?\d+)", t, flags=re.I)
    if m:
        staff_name = m.group(1).title()
        field_raw = m.group(2)
        value = int(m.group(3))
        field = normalize_field_name(field_raw)
        return {"type": "update_staff", "staff_name": staff_name, "field": field, "value": value}

    # Increase/Decrease Friday staff requirement by N
    m = re.match(r"(increase|decrease|reduce|raise)\s+([a-z]{3,})\s+staff\s+requirement\s+by\s+(-?\d+)", t, flags=re.I)
    if m:
        verb, day, delta = m.groups()
        day_norm = day[:3].title()
        delta = int(delta)
        sign = 1 if verb.lower() in ("increase", "raise") else -1
        return {"type": "update_demand_delta", "day": day_norm, "delta": sign * delta}

    # Set Friday staff requirement to N
    m = re.match(r"set\s+([a-z]{3,})\s+staff\s+requirement\s+to\s+(-?\d+)", t, flags=re.I)
    if m:
        day, value = m.groups()
        day_norm = day[:3].title()
        return {"type": "update_demand", "day": day_norm, "value": int(value)}

    return None


def apply_instruction(instruction, df_staff, df_demand):
    """Apply a structured instruction dict to update dataframes."""
    if not isinstance(instruction, dict):
        return False, "Instruction is not valid."

    cmd_type = instruction.get("type")

    if cmd_type == "update_staff":
        name = instruction.get("staff_name")
        field = normalize_field_name(instruction.get("field"))
        value = instruction.get("value")
        if name in df_staff["Staff Name"].values and field in df_staff.columns:
            df_staff.loc[df_staff["Staff Name"] == name, field] = value
            return True, f"Updated {name} - {field} set to {value}."
        return False, "Invalid staff name or field."

    elif cmd_type == "update_demand":
        day = instruction.get("day")
        value = instruction.get("value")
        if day in df_demand["Day"].values:
            df_demand.loc[df_demand["Day"] == day, "Staff Required"] = int(value)
            return True, f"Updated {day} staff requirement to {value}."
        return False, "Invalid day."

    elif cmd_type == "update_demand_delta":
        day = instruction.get("day")
        delta = instruction.get("delta")
        if day in df_demand["Day"].values:
            current = int(df_demand.loc[df_demand["Day"] == day, "Staff Required"].iloc[0])
            new_val = max(0, current + int(delta))
            df_demand.loc[df_demand["Day"] == day, "Staff Required"] = new_val
            return True, f"Updated {day} staff requirement by {delta} → {new_val}."
        return False, "Invalid day."

    return False, "Unknown command type."


# -----------------------------
# Streamlit main app
# -----------------------------

st.set_page_config(page_title="Optimisable – Workforce Scheduler", layout="wide")
st.title("Optimisable – Smart Workforce Scheduler")

# Step 1: Daily Staffing Requirements
st.header("Step 1: Define Daily Staffing Requirements")
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Use stored version if available, else initialise
if "demand" not in st.session_state:
    st.session_state.demand = pd.DataFrame({
        "Day": days,
        "Staff Required": [3, 3, 3, 3, 3, 5, 5]
    })

df_demand = st.data_editor(
    st.session_state.demand,
    num_rows="dynamic",
    width="stretch",
    key="demand_editor"
)

# Persist user edits live
st.session_state.demand = df_demand.copy()


# Step 2: Staff Details
st.header("Step 2: Define Staff Details")
if "staff" not in st.session_state:
    st.session_state.staff = pd.DataFrame({
        "Staff Name": [f"Staff {i+1}" for i in range(7)],
        "Staff Cost": [100]*7,
        "Min Working Days per Week": [3]*7,
        "Max Working Days per Week": [5]*7
    })

df_staff = st.data_editor(st.session_state.staff, num_rows="dynamic", width="stretch")

if len(df_staff) == 0:
    st.warning("At least one staff member is required.")
    st.stop()

# Run optimisation
if st.button("Run Optimisation"):
    with st.spinner("Optimising schedule..."):
        df_demand = st.session_state.demand.copy()
        result = optimiser.optimise_schedule(df_staff, df_demand)
        st.session_state["result"] = result

# Display result
if "result" in st.session_state:
    result = st.session_state["result"]
    if "Message" in result.columns:
        st.error(result.loc[0, "Message"])
    else:
        st.success("Optimisation complete.")
        st.subheader("Optimal Weekly Schedule")
        st.dataframe(result.style.format("{:.0f}"), width="stretch")
        if "Cost" in result.columns and "Total" in result.index:
            total_cost = result.loc["Total", "Cost"]
            st.write(f"**Total Weekly Cost:** £{int(total_cost):,}")

# Step 3: AI Assistant
st.header("Step 3: Ask or Instruct the AI Assistant")

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "result" in st.session_state and "Message" not in st.session_state["result"].columns:
    user_input = st.text_input(
        "Ask or instruct (e.g. 'Who works on Friday?' or 'Set Staff 3 cost to 90'):",
        key="chat_input"
    )
    send = st.button("Send")

    if send and user_input:
        result = st.session_state["result"]
        df_staff = st.session_state.staff.copy()
        df_demand = st.session_state.demand.copy()
        table_context = result.to_csv(index=True)

        system_prompt = (
            "You are an assistant managing a workforce schedule.\n"
            "You can either:\n"
            "(1) Answer questions based on the given table; or\n"
            "(2) Output a STRICT JSON object to modify configuration.\n"
            "Use DOUBLE QUOTES for JSON keys and values.\n"
            "Examples:\n"
            '{"type":"update_staff","staff_name":"Staff 3","field":"Staff Cost","value":90}\n'
            '{"type":"update_demand","day":"Fri","value":2}\n'
            '{"type":"update_demand_delta","day":"Fri","delta":-1}\n\n'
            f"Here is the current schedule:\n{table_context}"
        )

        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
            )
            response_text = completion.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Chat request failed: {e}")
            response_text = ""

        instruction = extract_json_object(response_text)
        if instruction is None:
            instruction = fallback_parse_command(user_input)

        if instruction is not None:
            ok, msg = apply_instruction(instruction, df_staff, df_demand)
            if ok:
                st.session_state.staff = df_staff
                st.session_state.demand = df_demand
                new_result = optimiser.optimise_schedule(df_staff, df_demand)
                st.session_state["result"] = new_result
                st.success(msg)
                st.rerun()
            else:
                st.warning(msg)
        else:
            if not response_text:
                response_text = "I could not interpret your request. Try phrasing it as: 'Set Staff 2 cost to 110' or 'Reduce Friday staff requirement by 1'."
            st.session_state.chat_history.append((user_input, response_text))
else:
    st.info("Please run the optimisation first before chatting.")

if st.session_state.chat_history:
    st.markdown("### Conversation History")
    for q, a in reversed(st.session_state.chat_history[-5:]):
        st.markdown(f"**You:** {q}")
        st.markdown(f"**AI:** {a}")
        st.markdown("---")
