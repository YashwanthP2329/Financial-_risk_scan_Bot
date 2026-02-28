# =========================
# IMPORTS
# =========================
import re
import streamlit as st
import ollama
from pypdf import PdfReader

# =========================
# CONFIG
# =========================
CHAT_MODEL = "phi3:mini"
MAX_CONTEXT_CHARS = 3000
# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Financial Risk Scanner", layout="wide")

# =========================
# CUSTOM UI DESIGN
# =========================
st.markdown("""
<style>
.main { background-color: #0f172a; }
h1, h2 { color: #38bdf8; }
.stButton>button {
    background-color: #1e293b;
    color: white;
    border-radius: 8px;
    height: 3em;
    width: 100%;
}
.card {
    padding: 20px;
    border-radius: 10px;
    background-color: #1e293b;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

st.title("📄 Financial Document Risk Scanner")

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
You are a Financial Risk Assessment AI.

STRICT RULES:
- Use ONLY the provided extracted clauses.
- Do NOT explain clause meanings.
- Do NOT fabricate information.
- Do NOT provide legal advice.
- Focus strictly on financial, legal, and long-term risk impact.

Output MUST follow this exact structure:

## Overall Financial Exposure
Detailed explanation of monetary risk and cost burden.

## Legal Vulnerability
Explain contractual, compliance, or regulatory risks.

## Long-Term Risk Impact
Describe sustainability concerns and future liabilities.

## Risk Severity Classification
Justify why the document is Low, Medium, or High risk.

## Advisory Recommendation
Provide professional cautionary guidance.
"""

# =========================
# FILE TEXT EXTRACTION
# =========================
def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")

    elif uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    return ""

# =========================
# STEP 1 — PROCESS DOCUMENT
# =========================
def process_document(text):

    # Extract relevant clauses
    keywords = [
        "year", "%", "return",
        "commission", "charge",
        "penalty", "increase",
        "reserves the right"
    ]

    lines = text.split("\n")
    relevant = []

    for line in lines:
        for word in keywords:
            if word in line.lower():
                relevant.append(line)
                break

    extracted_text = "\n".join(relevant)[:MAX_CONTEXT_CHARS]

    # Risk Detection
    risk_score = 0
    issues = []
    text_lower = text.lower()

    if re.search(r'(\d+)\s*year', text_lower):
        risk_score += 20
        issues.append("Long Lock-in Period")

    percentages = re.findall(r'(\d+)%', text_lower)
    for p in percentages:
        if int(p) > 50:
            risk_score += 20
            issues.append("High Percentage Charge")
            break

    if re.search(r'increase.*?(\d+)%', text_lower):
        risk_score += 20
        issues.append("Premium Escalation Risk")

    if "reserves the right" in text_lower:
        risk_score += 10
        issues.append("Unilateral Modification Clause")

    if risk_score >= 60:
        level = "High"
    elif risk_score >= 30:
        level = "Medium"
    else:
        level = "Low"

    return extracted_text, risk_score, level, issues

# =========================
# STEP 2 — GENERATE RISK SUMMARY
# =========================
def generate_risk_summary(extracted_text, score, level, issues):

    prompt = f"""
Extracted Risk Clauses:
{extracted_text}

Detected Issues:
{issues}

Risk Score: {score}
Risk Level: {level}

Generate structured financial risk assessment.
Follow the required heading format strictly.
"""

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        options={
            "num_predict": 1000,
            "temperature": 0.3
        }
    )

    return response["message"]["content"]

# =========================
# FILE UPLOAD
# =========================
uploaded_file = st.file_uploader(
    "Upload Policy Document (PDF or TXT)",
    type=["pdf", "txt"]
)

if uploaded_file:

    # Auto reset if new file uploaded
    if "last_file" not in st.session_state or st.session_state.last_file != uploaded_file.name:
        st.session_state.clear()
        st.session_state.last_file = uploaded_file.name

    document_text = extract_text_from_file(uploaded_file)

    col1, col2 = st.columns(2)

    # PROCESS BUTTON
    if col1.button("🔍 Process Document"):
        with st.spinner("Processing document and detecting risks..."):
            extracted, score, level, issues = process_document(document_text)
            st.session_state.extracted = extracted
            st.session_state.score = score
            st.session_state.level = level
            st.session_state.issues = issues

    # SUMMARY BUTTON
    if col2.button("📑 Generate Risk Summary"):
        if "extracted" in st.session_state:
            with st.spinner("Generating structured risk assessment..."):
                summary = generate_risk_summary(
                    st.session_state.extracted,
                    st.session_state.score,
                    st.session_state.level,
                    st.session_state.issues
                )
                st.session_state.summary = summary
        else:
            st.warning("Please process the document first.")

    st.markdown("---")

    # DISPLAY RESULTS
    if "extracted" in st.session_state:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Extracted Risk Clauses")
        st.text_area("Relevant Clauses", st.session_state.extracted, height=200)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Risk Assessment Overview")
        st.markdown(f"**Risk Level:** {st.session_state.level}")
        st.progress(st.session_state.score / 100)
        st.markdown(f"**Risk Score:** {st.session_state.score}/100")

        if st.session_state.issues:
            for issue in st.session_state.issues:
                st.markdown(f"- {issue}")

        st.markdown('</div>', unsafe_allow_html=True)

    if "summary" in st.session_state:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Structured Risk Summary")
        st.markdown(st.session_state.summary)
        st.markdown('</div>', unsafe_allow_html=True)

    st.caption("AI-assisted risk assessment. Not legal advice.")