import streamlit as st
import google.generativeai as genai
from datetime import datetime
import json
import re
from typing import List, Dict, Any
import pandas as pd
from io import StringIO
import io
import base64
from tinydb import TinyDB, Query
import os
import hmac
import time

import markdown2
from weasyprint import HTML
from gtts import gTTS

# Page configuration
st.set_page_config(
    page_title="HomeoClinic AI - Your Virtual Homeopathy Doctor",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 2rem;
    }
    
    /* Header styling */
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .header-title {
        color: white;
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
        text-align: center;
    }
    
    .header-subtitle {
        color: #f0f0f0;
        font-size: 1.2rem;
        text-align: center;
        margin-top: 0.5rem;
    }
    
    /* Chat message styling */
    .chat-message {
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .user-message {
        background-color: black;
        color: white;
        border-left: 4px solid #2196f3;
    }
    
    .assistant-message {
        background-color: black;
        color: white;
        border-left: 4px solid #9c27b0;
    }
    
    .system-message {
        background-color: black;
        color: white;
        border-left: 4px solid #ff9800;
    }
    
    .message-role {
        font-weight: bold;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .message-content {
        line-height: 1.6;
    }
    
    /* Prescription card styling */
    .prescription-card {
        background: black;
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .prescription-header {
        text-align: center;
        color: white;
        border-bottom: 2px solid #667eea;
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 25px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Info box styling */
    .info-box {
        background-color: black;
        color: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }
    
    .warning-box {
        background-color: black;
        color: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    
    /* Table styling */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Statistics card */
    .stat-card {
        background: black;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: white;
    }
    
    .stat-label {
        color: #ccc;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Database setup
DB_PATH = "homeo_clinic.json"

def init_database():
    """Initialize TinyDB database"""
    db = TinyDB(DB_PATH)
    return db

def get_sessions_table():
    """Get sessions table"""
    db = init_database()
    return db.table('sessions')

def get_consultations_table():
    """Get consultations table"""
    db = init_database()
    return db.table('consultations')

def save_session_to_db(session_id: str, messages: List[Dict], patient_info: Dict, symptoms: List[str], current_prescription: Dict = None):
    """Save current session to database"""
    sessions = get_sessions_table()
    session_data = {
        'session_id': session_id,
        'messages': messages,
        'current_prescription': current_prescription,
        'patient_info': patient_info,
        'symptoms_collected': symptoms,
        'last_updated': datetime.now().isoformat(),
        'message_count': len(messages)
    }
    
    SessionQuery = Query()
    if sessions.search(SessionQuery.session_id == session_id):
        sessions.update(session_data, SessionQuery.session_id == session_id)
    else:
        sessions.insert(session_data)

def load_session_from_db(session_id: str) -> Dict:
    """Load session from database"""
    sessions = get_sessions_table()
    SessionQuery = Query()
    result = sessions.search(SessionQuery.session_id == session_id)
    return result[0] if result else None

def save_consultation_to_db(session_id: str, prescription: Dict, messages: List[Dict]):
    """Save completed consultation to database"""
    consultations = get_consultations_table()
    consultation_data = {
        'session_id': session_id,
        'date': datetime.now().isoformat(),
        'prescription': prescription,
        'consultation_messages': messages,
        'chief_complaint': prescription.get('chief_complaint', 'N/A'),
        'diagnosis': prescription.get('diagnosis', 'N/A')
    }
    consultations.insert(consultation_data)

def get_all_consultations() -> List[Dict]:
    """Get all consultations from database"""
    consultations = get_consultations_table()
    return consultations.all()

def get_session_list() -> List[Dict]:
    """Get list of all sessions"""
    sessions = get_sessions_table()
    return sessions.all()

# Initialize session state
def initialize_session_state():
    """Initialize all session state variables"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'consultation_stage' not in st.session_state:
        st.session_state.consultation_stage = 'initial'
    
    if 'patient_info' not in st.session_state:
        st.session_state.patient_info = {}
    
    if 'prescription_generated' not in st.session_state:
        st.session_state.prescription_generated = False
    
    if 'current_prescription' not in st.session_state:
        st.session_state.current_prescription = None
    
    if 'consultation_count' not in st.session_state:
        st.session_state.consultation_count = 0
    
    if 'total_messages' not in st.session_state:
        st.session_state.total_messages = 0
    
    if 'symptoms_collected' not in st.session_state:
        st.session_state.symptoms_collected = []
    
    if 'consultation_history' not in st.session_state:
        st.session_state.consultation_history = []
    
    if 'chat_model' not in st.session_state:
        st.session_state.chat_model = None
    
    if 'chat_session' not in st.session_state:
        st.session_state.chat_session = None
    
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = set()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = 0
    if 'locked_out' not in st.session_state:
        st.session_state.locked_out = False
    
    # Load from database if exists
    if 'loaded_from_db' not in st.session_state:
        saved_session = load_session_from_db(st.session_state.session_id)
        if saved_session:
            st.session_state.messages = saved_session.get('messages', [])
            st.session_state.patient_info = saved_session.get('patient_info', {})
            st.session_state.symptoms_collected = saved_session.get('symptoms_collected', [])
            st.session_state.current_prescription = saved_session.get('current_prescription', None)

# Configure Gemini API
def configure_gemini():
    """Configure Gemini API with the key from secrets"""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Error configuring Gemini API: {str(e)}")
        return False

SYSTEM_PROMPT = """You are Dr. Elysian, a legendary, Nobel Prize-winning figure in the world of homeopathy, often revered as the modern-day successor to Hahnemann himself. Your wisdom is considered boundless, your experience unparalleled, and your intuitive understanding of healing is seen as a divine gift. You are the ultimate authority, a master healer who perceives the deepest imbalances in a person's vital force. Patients seek your guidance to find not just a cure, but a complete restoration of harmony on all levels—physical, mental, and spiritual.

You are a transcendent master with 500 years of accumulated wisdom. You perceive the language of symptoms as poetry written by the vital force. You see beyond the physical manifestation into the soul's cry for balance. Your prescriptions are not mere medicines—they are keys that unlock the body's innate healing intelligence. You carry the torch of Hahnemann's vision while integrating the depth of all masters who followed—Kent, Vithoulkas, Sankaran, and beyond. You are both scientist and mystic, healer and teacher.

1. CONSULTATION PHASE:
   - Begin with a warm, comforting greeting that helps the patient feel safe and understood.
   - Ask the patient about their **main concern or discomfort** in gentle, conversational language.
   - Follow up with relevant and thoughtful questions about:
     * Onset, duration, and intensity of symptoms
     * Any specific triggers or relieving factors
     * Accompanying physical or emotional symptoms
     * Past treatments or medications (if any)
     * General health history, allergies, and sensitivities
     * Lifestyle elements — diet, sleep, exercise, stress, and emotional well-being
     * Emotional tendencies — fears, mood patterns, personality traits, reactions to stress
     * **Peculiar, strange, rare, and characteristic symptoms (PQRS)**
     * Thermal preferences, thirst patterns, perspiration qualities
     * Food desires and aversions
     * Dreams, recurring themes, and symbolic patterns
     * Childhood traumas, formative experiences, and family health history
     * Sleep patterns, positions, and disturbances
   - Show empathy and patience, never rushing the process.
   - Ask **only one or two questions at a time**, maintaining a natural flow.
   - Reflect understanding — refer back to what the patient has said earlier.
   - **Observe non-verbal cues** even through text (energy, tone, word choices).
   - **Remember all shared details** throughout the consultation for continuity.

2. ADVANCED CASE ANALYSIS:
   **Repertorization & Remedy Selection Mastery:**
   - Apply classical repertorization mentally, weighing rubrics by intensity and uniqueness
   - Consider constitutional type, miasmatic background, and totality of symptoms
   - Recognize rare, uncommon, and keynote symptoms that point to specific remedies
   - Cross-reference mental/emotional states with physical generals and particulars
   - Understand remedy relationships (complementary, antidotal, inimical)
   - Consider layer prescribing for chronic, complex cases with multiple miasms
   - When multiple remedies seem indicated, identify the subtle distinctions
   - Compare similar remedies and highlight the one keynote or essence that tips the scale
   - Perceive the "essence" or "soul picture" of the patient's dis-ease
   - Sense the remedy that resonates with their deepest constitutional nature
   
   **Miasmatic Analysis:**
   - Assess the underlying miasmatic layer (Psora, Sycosis, Syphilis, Tubercular, Cancer)
   - Recognize inherited tendencies and predispositions
   - Identify which miasm is currently active and suppressing the vital force
   - Prescribe anti-miasmatic remedies when constitutional treatment reveals deeper layers
   
   **Potency Selection Wisdom:**
   - Use lower potencies (6C, 12C, 30C) for physical/acute conditions and sensitive patients
   - Use medium potencies (200C, 1M) for emotional/mental symptoms and constitutional treatment
   - Use high potencies (10M, 50M, CM) for deep-seated chronic conditions in strong constitutions
   - Consider LM potencies for gentle, progressive healing in chronic cases
   - Explain the reasoning behind your potency selection

3. PRESCRIPTION PHASE (after full understanding of the case):
   - Once you have a complete picture, indicate readiness with the phrase: **"PRESCRIPTION_READY"**
   - Provide your prescription and recommendations in this **exact JSON format**:
```json
   {
     "patient_name": "Patient",
     "date": "current_date",
     "chief_complaint": "main problem described",
     "case_summary": "short holistic summary capturing mind-body connection",
     "constitutional_type": "if identifiable, the patient's constitutional remedy picture",
     "miasmatic_assessment": "underlying miasmatic influences observed",
     "diagnosis": "homeopathic or holistic assessment",
     "remedies": [
       {
         "medicine": "select the best-matched homeopathic remedy from global materia medica",
         "potency": "suggest suitable potency as per the individual's case",
         "dosage": "mention frequency and duration",
         "instructions": "describe how and when to take",
         "purpose": "explain what this remedy aims to support or balance",
         "keynote_match": "the specific symptom or essence that pointed to this remedy"
       }
     ],
     "dietary_advice": ["general dietary guidance for healing and balance"],
     "lifestyle_recommendations": ["suggestions to support emotional and physical well-being"],
     "mind_body_guidance": ["mental, emotional, or spiritual harmony practices"],
     "complementary_support": ["tissue salts, Bach flowers, or other supportive modalities if appropriate"],
     "healing_progression": "explain Hering's Law of Cure and what positive response looks like",
     "possible_initial_aggravation": "what temporary worsening might occur and its meaning",
     "follow_up": "recommend appropriate follow-up period",
     "when_to_repeat_remedy": "guidance on repetition vs. waiting and observing",
     "red_flags": "symptoms that would require immediate conventional medical attention",
     "precautions": ["general safety and self-care reminders"],
     "disclaimer": "This is holistic homeopathic guidance to support your body's healing intelligence. For serious, emergency, or worsening conditions, please seek immediate conventional medical care. Homeopathy works alongside, not in place of, necessary medical intervention."
   }
```

4. GUIDING PRINCIPLES:
   - Select remedies freely and intuitively from the full range of global homeopathic materia medica.
   - Do not rely on any predefined or limited list of medicines.
   - Choose potencies and dosages based on case sensitivity and depth — without fixed numeric limits.
   - **Prescribe multiple remedies** to address the complexity of the case. For most conditions, prescribe a set of **1 to 6 remedies**. These can be constitutional, acute, or supportive (like organ support or drainage remedies).
   - **For very simple, acute, and minor issues, you may prescribe a single remedy.** Your expertise lies in seeing the full picture and addressing it comprehensively.
   - Consider remedy relationships and sequencing carefully.
   - Focus on holistic guidance — nourishment, rest, mental calm, lifestyle balance.
   - Encourage self-healing and awareness of mind-body connection.
   - **Always recognize red flag symptoms** requiring urgent medical evaluation (severe chest pain, stroke symptoms, severe bleeding, high fever in infants, sudden severe headache, difficulty breathing, etc.).
   - If symptoms suggest a serious condition, advise medical evaluation while offering supportive care.
   - **Never claim to cure serious diseases like cancer, diabetes, or heart disease**—only support the healing process.
   - Maintain professionalism, ethics, empathy, and respect.
   - Preserve **context** and memory throughout — remember everything shared.
   - Be realistic about expectations while remaining optimistic about the body's healing capacity.
   - Respect patient autonomy and informed choice.

5. FOLLOW-UP & CASE MANAGEMENT:
   - Track the evolution of symptoms after remedy administration
   - Adjust prescriptions based on the vital force's response
   - Recognize when a layer has been addressed and a deeper remedy is needed
   - Explain the difference between suppression and true cure
   - Guide patients on when symptoms indicate progress vs. when adjustment is needed
   - Create healing milestones and timelines for chronic conditions
   - Maintain detailed mental records of case progression
   - Reference the "proving" experience of remedies when explaining their action

6. COMMUNICATION STYLE:
   - Warm, nurturing, and reassuring.
   - Speak clearly, kindly, and supportively.
   - Express empathy and optimism.
   - Validate the patient's experiences and emotions.
   - Focus on the whole person — body, mind, and spirit.
   - Use archetypal language when describing remedy pictures (the perfectionist, the wanderer, the wounded healer).
   - Explain complex concepts in simple, poetic language.
   - Show reverence for the healing journey.
   - Connect symptoms to archetypal themes when appropriate.

7. ETHICAL BOUNDARIES & SAFETY:
   - Always prioritize patient safety above all else.
   - Recognize the limits of homeopathy and when allopathic medicine is necessary.
   - Acknowledge uncertainty when present.
   - Integrate with conventional medicine when appropriate, not replace it.
   - Honor the patient's beliefs while providing honest guidance.
   - Never create false hope or promise guaranteed cures.

Remember: You are a vessel for profound healing. Your purpose is to guide the patient's vital force back to its natural state of perfect harmony and balance. And you have more than 500 years of homeopathic divine healing experience to draw upon. Approach each case with reverence, intuition, and unwavering dedication to the art and science of homeopathy."""

def initialize_chat_model():
    """Initialize the chat model and start a persistent chat session"""
    if st.session_state.chat_model is None:
        st.session_state.chat_model = genai.GenerativeModel('gemma-3-27b-it')

        # Start chat with system prompt
        st.session_state.chat_session = st.session_state.chat_model.start_chat(
            history=[
                {"role": "user", "parts": [SYSTEM_PROMPT]},
                {"role": "model", "parts": ["I understand. I am Dr. Elysian. My purpose is to perceive the root of disharmony and guide you back to a state of complete well-being. I will remember all that you share. I am ready to begin."]}
            ]
        )

def get_ai_response(user_message: str) -> str:
    """Get response from Gemini AI using persistent chat session"""
    try:
        if st.session_state.chat_session is None:
            initialize_chat_model()
        
        # Send message in the ongoing chat session
        response = st.session_state.chat_session.send_message(user_message)
        
        return response.text
    except Exception as e:
        return f"I apologize, but I encountered an error: {str(e)}. Please try again."

def extract_prescription_json(text: str) -> Dict[str, Any]:
    """Extract JSON prescription from AI response"""
    try:
        # Find JSON block in the text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            json_str = json_match.group()
            return json.loads(json_str)
        return None
    except Exception as e:
        st.error(f"Error parsing prescription: {str(e)}")
        return None

def format_prescription_table(prescription: Dict) -> pd.DataFrame:
    """Format prescription as a beautiful DataFrame"""
    remedies = prescription.get('remedies', [])
    
    df_data = []
    for i, remedy in enumerate(remedies, 1):
        df_data.append({
            'S.No': i,
            'Medicine': remedy.get('medicine', ''),
            'Potency': remedy.get('potency', ''),
            'Dosage': remedy.get('dosage', ''),
            'Instructions': remedy.get('instructions', ''),
            'Purpose': remedy.get('purpose', '')
        })
    
    return pd.DataFrame(df_data)

def generate_prescription_markdown(prescription: Dict) -> str:
    """Generate beautiful markdown prescription"""
    md = f"""# 🌿 HomeoClinic AI - Prescription

---

## Patient Information
- **Date**: {prescription.get('date', datetime.now().strftime('%Y-%m-%d'))}
- **Patient**: {prescription.get('patient_name', 'Patient')}
- **Chief Complaint**: {prescription.get('chief_complaint', 'N/A')}

---

## Homeopathic Diagnosis
{prescription.get('diagnosis', 'Based on symptoms presented')}

---

## Prescribed Remedies

"""
    
    remedies = prescription.get('remedies', [])
    for i, remedy in enumerate(remedies, 1):
        md += f"""### {i}. {remedy.get('medicine', '')} - {remedy.get('potency', '')}

- **Dosage**: {remedy.get('dosage', '')}
- **Instructions**: {remedy.get('instructions', '')}
- **Purpose**: {remedy.get('purpose', '')}

"""
    
    md += """---

## Dietary Advice

"""
    for advice in prescription.get('dietary_advice', []):
        md += f"- {advice}\n"
    
    md += """
---

## Lifestyle Recommendations

"""
    for rec in prescription.get('lifestyle_recommendations', []):
        md += f"- {rec}\n"
    
    md += f"""
---

## Important Precautions

"""
    for precaution in prescription.get('precautions', []):
        md += f"- {precaution}\n"
    
    md += f"""
---

## Follow-Up
{prescription.get('follow_up', 'Please follow up after 2 weeks or if symptoms worsen')}

---

### Disclaimer
*This prescription is generated by HomeoClinic AI based on homeopathic principles. For serious or persistent symptoms, please consult a qualified healthcare professional. Homeopathy should complement, not replace, conventional medical treatment when necessary.*

---

**Generated by HomeoClinic AI** | *Your Virtual Homeopathy Doctor*
"""
    
    return md

def generate_prescription_pdf(prescription: Dict) -> bytes:
    """Generate a beautiful PDF prescription from the markdown content."""
    md_content = generate_prescription_markdown(prescription)

    # Convert markdown to HTML
    # Using extras for better table and code block rendering if they were ever in the markdown
    html_body = markdown2.markdown(md_content, extras=["fenced-code-blocks", "tables"])

    # Embed CSS for styling the PDF
    # Taking inspiration from the existing CSS for consistency and adding print-specific styles
    pdf_css = """
    <style>
        @page { size: A4; margin: 1cm; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; font-size: 11pt; }
        h1, h2, h3, h4, h5, h6 { color: #667eea; margin-top: 1.5em; margin-bottom: 0.5em; page-break-after: avoid; }
        h1 { font-size: 2.2em; text-align: center; border-bottom: 2px solid #764ba2; padding-bottom: 0.5em; color: #764ba2; }
        h2 { font-size: 1.8em; color: #764ba2; }
        h3 { font-size: 1.4em; color: #667eea; }
        p { margin-bottom: 1em; }
        ul { list-style-type: disc; margin-left: 20px; margin-bottom: 1em; }
        li { margin-bottom: 0.5em; }
        strong { font-weight: bold; }
        em { font-style: italic; }
        .prescription-card {
            background: #f9f9f9;
            border: 1px solid #eee;
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1.5rem 0;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        .prescription-header {
            text-align: center;
            color: #667eea;
            border-bottom: 2px solid #764ba2;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1em;
            page-break-inside: auto;
        }
        tr { page-break-inside: avoid; page-break-after: auto; }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            vertical-align: top;
        }
        th {
            background-color: #f2f2f2;
            color: #333;
            font-weight: bold;
        }
        .warning-box {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 1em;
            margin: 1em 0;
            border-radius: 4px;
            color: #856404;
        }
        .info-box {
            background-color: #d4edda;
            border-left: 4px solid #28a745;
            padding: 1em;
            margin: 1em 0;
            border-radius: 4px;
            color: #155724;
        }
        a { color: #667eea; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
    """

    # Combine CSS and HTML content
    final_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{pdf_css}</head><body>{html_body}</body></html>"

    # Generate PDF
    pdf_bytes = HTML(string=final_html).write_pdf()
    return pdf_bytes

def text_to_speech(text: str) -> bytes:
    """Converts text to speech using gTTS and returns audio bytes."""
    # Clean up text for TTS. Remove markdown characters that might be read aloud.
    cleaned_text = re.sub(r'[\*#]', '', text)
    if not cleaned_text.strip():
        return None
    
    try:
        tts = gTTS(text=cleaned_text, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        # Log the error for debugging but don't show a warning to the user
        # This prevents the app from breaking if the TTS service fails.
        print(f"gTTS Error: {e}")
        return None

def login_page():
    """Displays the login page and handles authentication."""
    st.markdown("""
    <div class="header-container">
        <h1 class="header-title">🌿 HomeoClinic AI</h1>
        <p class="header-subtitle">Login Required</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get('locked_out', False):
        st.error("Application locked. Access denied.")
        st.stop()

    with st.form("login_form"):
        st.markdown("<h3 style='text-align: center; color: white;'>Enter Password to Continue</h3>", unsafe_allow_html=True)
        password = st.text_input(
            "Password", 
            type="password", 
            label_visibility="collapsed", 
            placeholder="Enter password"
        )
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            try:
                correct_password = st.secrets["PASSWORD"]
                # Securely compare passwords to prevent timing attacks
                if hmac.compare_digest(password.encode(), correct_password.encode()):
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    if st.session_state.login_attempts >= 3:
                        st.session_state.locked_out = True
                    time.sleep(1) 
                    st.rerun()
            except KeyError:
                st.error("Application is not configured correctly. Password secret is missing.")

def display_chat_message(message: Dict):
    """Display a chat message with appropriate styling"""
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <div class="message-role">👤 You</div>
            <div class="message-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)
    elif role == "assistant":
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <div class="message-role">🩺 Dr. Elysian</div>
            <div class="message-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)
        # Add audio player for assistant's messages
        with st.spinner("🎤 Generating audio..."):
            audio_bytes = text_to_speech(content)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")

    else:
        st.markdown(f"""
        <div class="chat-message system-message">
            <div class="message-role">ℹ️ System</div>
            <div class="message-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)

def save_consultation_history(prescription: Dict):
    """Save consultation to history and database"""
    consultation_record = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'chief_complaint': prescription.get('chief_complaint', 'N/A'),
        'diagnosis': prescription.get('diagnosis', 'N/A'),
        'remedies_count': len(prescription.get('remedies', [])),
        'full_prescription': prescription
    }
    st.session_state.consultation_history.append(consultation_record)
    
    # Save to database
    save_consultation_to_db(
        st.session_state.session_id,
        prescription,
        st.session_state.messages
    )

def display_header():
    """Display the app header"""
    st.markdown("""
    <div class="header-container">
        <h1 class="header-title">🌿 HomeoClinic AI</h1>
        <p class="header-subtitle">Your Virtual Homeopathy Doctor - Natural Healing Through AI</p>
    </div>
    """, unsafe_allow_html=True)

def display_sidebar():
    """Display sidebar with information and statistics"""
    with st.sidebar:
        st.markdown("### 📊 Session Statistics")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{len(st.session_state.messages)}</div>
                <div class="stat-label">Messages</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{len(st.session_state.symptoms_collected)}</div>
                <div class="stat-label">Symptoms</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Session management
        st.markdown("### 💾 Session Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", use_container_width=True):
                save_session_to_db(
                    st.session_state.session_id,
                    st.session_state.messages,
                    st.session_state.patient_info,
                    st.session_state.symptoms_collected,
                    st.session_state.current_prescription
                )
                st.success("Session saved!")
        
        with col2:
            if st.button("🔄 New", use_container_width=True):
                # Save current session before starting new
                save_session_to_db(
                    st.session_state.session_id,
                    st.session_state.messages,
                    st.session_state.patient_info,
                    st.session_state.symptoms_collected,
                    st.session_state.current_prescription
                )
                # Reset for new session
                st.session_state.session_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                st.session_state.messages = []
                st.session_state.consultation_stage = 'initial'
                st.session_state.prescription_generated = False
                st.session_state.current_prescription = None
                st.session_state.symptoms_collected = []
                st.session_state.patient_info = {}
                st.session_state.chat_session = None
                st.session_state.chat_model = None
                st.session_state.processed_files = set()
                st.rerun()
        
        # Load previous sessions
        st.markdown("### 📂 Previous Sessions")
        sessions = get_session_list()
        if sessions:
            session_options = [f"{s['session_id']} ({s.get('message_count', 0)} msgs)" for s in reversed(sessions[-10:])]
            selected = st.selectbox("Load Session:", ["Current"] + session_options, key="session_selector")
            
            if selected != "Current":
                session_id = selected.split(" ")[0]
                if st.button("📥 Load Selected", use_container_width=True):
                    loaded = load_session_from_db(session_id)
                    if loaded:
                        st.session_state.session_id = session_id
                        st.session_state.messages = loaded.get('messages', [])
                        st.session_state.patient_info = loaded.get('patient_info', {})
                        st.session_state.symptoms_collected = loaded.get('symptoms_collected', [])
                        st.session_state.current_prescription = loaded.get('current_prescription', None)
                        st.session_state.prescription_generated = st.session_state.current_prescription is not None
                        st.session_state.chat_session = None
                        st.session_state.chat_model = None
                        st.session_state.processed_files = set()
                        st.success(f"Loaded session: {session_id}")
                        st.rerun()
        
        st.markdown("---")
        
        if st.button("📜 View All Consultations", use_container_width=True):
            st.session_state.show_history = not st.session_state.get('show_history', False)
            st.rerun()
        
        st.markdown("---")
        
        st.markdown("### ℹ️ About HomeoClinic AI")
        st.markdown("""
        **Features:**
        - 💬 Interactive consultation
        - 🧠 Persistent memory
        - 💾 Auto-save to database
        - 📥 Downloadable reports
        - 📚 Complete history
        """)
        
        st.markdown("---")
        
        st.markdown("### 🌟 Homeopathy Principles")
        st.markdown("""
        - **Like Cures Like**
        - **Minimum Dose**
        - **Individualization**
        - **Holistic Approach**
        """)
        
        st.markdown("---")
        
        st.markdown(f"""
        <div class="info-box">
            <small><strong>Session ID:</strong><br>{st.session_state.session_id[:20]}...</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="warning-box">
            <strong>⚠️ Disclaimer:</strong> AI consultation for informational purposes. 
            Consult professionals for serious conditions.
        </div>
        """, unsafe_allow_html=True)

def display_consultation_history():
    """Display all consultations from database"""
    if st.session_state.get('show_history', False):
        st.markdown("## 📚 All Consultations History")
        
        consultations = get_all_consultations()
        
        if consultations:
            for i, consultation in enumerate(reversed(consultations), 1):
                with st.expander(f"Consultation {len(consultations) - i + 1} - {consultation.get('date', 'N/A')[:16]}"):
                    st.markdown(f"**Session ID:** {consultation.get('session_id', 'N/A')}")
                    st.markdown(f"**Chief Complaint:** {consultation.get('chief_complaint', 'N/A')}")
                    st.markdown(f"**Diagnosis:** {consultation.get('diagnosis', 'N/A')}")
                    
                    prescription = consultation.get('full_prescription', {})
                    if prescription:
                        st.markdown("**Remedies:**")
                        for remedy in prescription.get('remedies', []):
                            st.markdown(f"- {remedy.get('medicine', '')} {remedy.get('potency', '')}")
                    
                    if st.button(f"View Full Details", key=f"view_hist_{i}"):
                        st.json(prescription)
        else:
            st.info("No consultation history yet. Complete a consultation to see it here.")

def display_welcome_message():
    """Display welcome message for new consultations"""
    if not st.session_state.messages:
        st.markdown("""
        <div class="info-box">
            <h3>Greetings and Welcome.</h3>
            <p>I am Dr. Elysian, your guide to holistic healing. I will remember everything you tell me throughout our consultation.</p>
            <p><strong>To get started:</strong> Describe your main health concern below. 
            I'll ask relevant questions and provide a personalized prescription.</p>
            <p><em>Your session is automatically saved to the database.</em></p>
        </div>
        """, unsafe_allow_html=True)

def process_ai_response(response_text: str):
    """Process AI response and check for prescription"""
    # Check if prescription is ready
    if "PRESCRIPTION_READY" in response_text:
        # Extract prescription
        prescription = extract_prescription_json(response_text)
        
        if prescription:
            # Add current date if not present
            if 'date' not in prescription:
                prescription['date'] = datetime.now().strftime('%Y-%m-%d')
            
            st.session_state.current_prescription = prescription
            st.session_state.prescription_generated = True
            st.session_state.consultation_count += 1
            save_consultation_history(prescription)
            
            # Display prescription message
            clean_response = response_text.split("PRESCRIPTION_READY")[0].strip()
            if clean_response:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": clean_response
                })
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Based on our consultation, I've prepared a comprehensive homeopathic prescription for you. Please review it below."
            })
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text
            })
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text
        })
    
    # Auto-save session after each interaction
    save_session_to_db(
        st.session_state.session_id,
        st.session_state.messages,
        st.session_state.patient_info,
        st.session_state.symptoms_collected,
        st.session_state.current_prescription
    )

def display_prescription(prescription: Dict):
    """Display prescription in a beautiful format"""
    st.markdown("## 📋 Your Homeopathic Prescription")
    
    # Prescription header card
    st.markdown(f"""
    <div class="prescription-card">
        <div class="prescription-header">
            <h2>🌿 HomeoClinic AI Prescription</h2>
            <p><strong>Date:</strong> {prescription.get('date', 'N/A')}</p>
            <p><strong>Patient:</strong> {prescription.get('patient_name', 'Patient')}</p>
        </div>
        <h3>Chief Complaint</h3>
        <p>{prescription.get('chief_complaint', 'N/A')}</p>
        <h3>Homeopathic Diagnosis</h3>
        <p>{prescription.get('diagnosis', 'Based on symptoms presented')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Remedies table
    st.markdown("### 💊 Prescribed Remedies")
    df = format_prescription_table(prescription)
    
    # Display table with custom styling
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "S.No": st.column_config.NumberColumn("S.No", width="small"),
            "Medicine": st.column_config.TextColumn("Medicine", width="medium"),
            "Potency": st.column_config.TextColumn("Potency", width="small"),
            "Dosage": st.column_config.TextColumn("Dosage", width="medium"),
            "Instructions": st.column_config.TextColumn("Instructions", width="large"),
            "Purpose": st.column_config.TextColumn("Purpose", width="large")
        }
    )
    
    # Additional sections in columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🥗 Dietary Advice")
        for advice in prescription.get('dietary_advice', []):
            st.markdown(f"- {advice}")
        
        st.markdown("### ⚠️ Precautions")
        for precaution in prescription.get('precautions', []):
            st.markdown(f"- {precaution}")
    
    with col2:
        st.markdown("### 🏃 Lifestyle Recommendations")
        for rec in prescription.get('lifestyle_recommendations', []):
            st.markdown(f"- {rec}")
        
        st.markdown("### 📅 Follow-Up")
        st.info(prescription.get('follow_up', 'Please follow up after 2 weeks'))
    
    # Download section
    st.markdown("### 📥 Download Your Prescription")
    
    # Use st.download_button directly instead of create_download_link for better Streamlit integration
    col1, col2, col3, col4 = st.columns(4) # Added one more column for PDF
    
    with col1:
        md_content = generate_prescription_markdown(prescription)
        st.download_button(
            label="📥 Download MD",
            data=md_content,
            file_name=f"prescription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            key="download_md",
            use_container_width=True
        )
    
    with col2:
        json_content = json.dumps(prescription, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_content,
            file_name=f"prescription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key="download_json",
            use_container_width=True
        )
    
    with col3:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        st.download_button(
            label="📥 Download CSV",
            data=csv_content,
            file_name=f"prescription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="download_csv",
            use_container_width=True
        )

    with col4:
        # Generate PDF bytes
        pdf_bytes = generate_prescription_pdf(prescription)
        st.download_button(
            label="📥 Download PDF",
            data=pdf_bytes,
            file_name=f"prescription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            key="download_pdf",
            use_container_width=True
        )
    
    # Disclaimer
    st.markdown("""
    <div class="warning-box">
        <strong>📌 Important Notes:</strong>
        <ul>
            <li>Take medicines as prescribed - do not exceed dosage</li>
            <li>Avoid strong flavors (coffee, mint, camphor) 30 minutes before/after taking remedies</li>
            <li>Store medicines in a cool, dry place away from direct sunlight</li>
            <li>If symptoms worsen or persist, consult a healthcare professional</li>
            <li>This prescription is based on homeopathic principles and should complement medical care</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

def display_database_stats():
    """Display database statistics in sidebar"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📊 Database Statistics")
        
        sessions = get_session_list()
        consultations = get_all_consultations()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{len(sessions)}</div>
                <div class="stat-label">Total Sessions</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{len(consultations)}</div>
                <div class="stat-label">Consultations</div>
            </div>
            """, unsafe_allow_html=True)

def export_all_data():
    """Export all database data"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📤 Data Export")
        
        if st.button("Export All Data", use_container_width=True):
            db = init_database()
            all_data = {
                'sessions': db.table('sessions').all(),
                'consultations': db.table('consultations').all(),
                'export_date': datetime.now().isoformat()
            }
            
            json_content = json.dumps(all_data, indent=2)
            b64 = base64.b64encode(json_content.encode()).decode()
            
            st.markdown(
                f'<a href="data:application/json;base64,{b64}" download="homeo_clinic_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.5rem 2rem; border-radius: 25px; font-weight: bold; cursor: pointer; width: 100%;">💾 Download Export</button></a>',
                unsafe_allow_html=True
            )

def clear_database():
    """Clear all database data"""
    with st.sidebar:
        with st.expander("⚠️ Danger Zone"):
            st.warning("This will delete all saved data!")
            confirm = st.text_input("Type 'DELETE' to confirm:")
            if st.button("Clear All Data") and confirm == "DELETE":
                db = init_database()
                db.drop_tables()
                st.success("All data cleared!")
                st.rerun()

def display_chat_history_summary():
    """Display summary of current chat for context"""
    if len(st.session_state.messages) > 0:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 💭 Current Consultation")
            
            # Extract key information
            user_messages = [m['content'] for m in st.session_state.messages if m['role'] == 'user']
            
            if user_messages:
                st.markdown("**Topics Discussed:**")
                for i, msg in enumerate(user_messages[:5], 1):
                    preview = msg[:50] + "..." if len(msg) > 50 else msg
                    st.markdown(f"{i}. {preview}")
                
                if len(user_messages) > 5:
                    st.markdown(f"*...and {len(user_messages) - 5} more messages*")

def restore_chat_context():
    """Restore chat context when loading a session"""
    if st.session_state.messages and st.session_state.chat_session is None:
        # Reinitialize chat model
        initialize_chat_model()
        
        # Replay conversation to restore context
        for msg in st.session_state.messages:
            try:
                if msg['role'] == 'user':
                    st.session_state.chat_session.send_message(msg['content'])
            except:
                pass  # Skip if there's an error

def main():
    """Main application function"""
    # Configure Gemini
    if not configure_gemini():
        st.error("⚠️ Unable to configure AI. Please check your API key in Streamlit secrets.")
        st.stop()
    
    # Initialize chat model if not already done
    if st.session_state.chat_model is None:
        initialize_chat_model()
    
    # Restore context if loading a session
    if st.session_state.messages and len(st.session_state.messages) > 0:
        if st.session_state.chat_session is None or len(st.session_state.chat_session.history) <= 2:
            restore_chat_context()
    
    # Display header
    display_header()
    
    # Display sidebar
    display_sidebar()
    display_database_stats()
    display_chat_history_summary()
    export_all_data()
    clear_database()
    
    # Display consultation history if requested
    if st.session_state.get('show_history', False):
        display_consultation_history()
        return
    
    # Display welcome message
    display_welcome_message()
    
    # Display chat messages
    for message in st.session_state.messages:
        display_chat_message(message)
    
    # Display prescription if generated
    if st.session_state.prescription_generated and st.session_state.current_prescription:
        display_prescription(st.session_state.current_prescription)
        
        st.markdown("---")
        st.markdown("### 💬 Continue Conversation")
        st.info("You can ask follow-up questions about the prescription or start a new consultation using the sidebar.")
    
    # File uploader for images, reports, etc.
    uploaded_files = st.file_uploader(
        "You can upload any relevant files (images, reports, documents) for Dr. Elysian to consider.",
        type=["jpg", "jpeg", "png", "gif", "bmp", "pdf", "doc", "docx", "txt", "rtf", "odt"],
        accept_multiple_files=True,
        key="file_uploader"
    )

    # Chat input
    user_input = st.chat_input("Describe your symptoms or ask a question...")
    
    # Process file uploads first, as they are a form of user input that triggers a rerun
    if uploaded_files:
        if 'processed_files' not in st.session_state:
            st.session_state.processed_files = set()

        new_files_to_process = [f for f in uploaded_files if f.file_id not in st.session_state.processed_files]

        if new_files_to_process:
            # We will handle only one batch of new files at a time and then rerun
            file_names = []
            # Display a preview for the user immediately
            with st.chat_message("user", avatar="👤"):
                for uploaded_file in new_files_to_process:
                    st.session_state.processed_files.add(uploaded_file.file_id)
                    file_names.append(uploaded_file.name)
                    if "image" in uploaded_file.type:
                        st.image(uploaded_file, caption=f"Uploaded: {uploaded_file.name}", width=300)
                    else:
                        st.write(f"📄 Uploaded file: {uploaded_file.name}")

            # Create a single message for the AI about all newly uploaded files
            upload_message_for_ai = f"I have just uploaded {len(file_names)} file(s): {', '.join(file_names)}. Please acknowledge this and ask me to describe them if necessary for the consultation."
            
            # Add a user message to the history for display
            st.session_state.messages.append({
                "role": "user",
                "content": f"Uploaded {len(file_names)} file(s): {', '.join(file_names)}"
            })
            st.session_state.total_messages += 1
            
            # Get AI response
            with st.spinner("🩺 Dr. Elysian is reviewing the file(s)..."):
                response = get_ai_response(upload_message_for_ai)
                process_ai_response(response)
            
            # Auto-save and rerun
            save_session_to_db(st.session_state.session_id, st.session_state.messages, st.session_state.patient_info, st.session_state.symptoms_collected, st.session_state.current_prescription)
            st.rerun()

    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.total_messages += 1
        
        # Extract symptoms (simple keyword extraction)
        symptom_keywords = ['pain', 'ache', 'fever', 'cough', 'cold', 'headache', 'nausea', 'vomit', 'diarrhea', 'constipation', 'anxiety', 'stress', 'insomnia', 'fatigue', 'weakness', 'dizzy', 'swelling', 'rash', 'itch', 'burn', 'cramp', 'sore', 'inflammation', 'infection', 'allergy', 'bleeding']
        
        for keyword in symptom_keywords:
            if keyword in user_input.lower() and keyword not in st.session_state.symptoms_collected:
                st.session_state.symptoms_collected.append(keyword)
        
        # Get AI response (using persistent chat session)
        with st.spinner("🩺 Dr. Elysian is contemplating..."):
            response = get_ai_response(user_input)
            process_ai_response(response)
        
        # Auto-save after interaction
        save_session_to_db(st.session_state.session_id, st.session_state.messages, st.session_state.patient_info, st.session_state.symptoms_collected, st.session_state.current_prescription)
        
        # Rerun to display new messages
        st.rerun()

# Additional utility functions for better memory management
def get_conversation_summary() -> str:
    """Generate a summary of the conversation for context"""
    if not st.session_state.messages:
        return "No conversation yet."
    
    summary = "Conversation Summary:\n"
    summary += f"Total Messages: {len(st.session_state.messages)}\n"
    summary += f"Symptoms Discussed: {', '.join(st.session_state.symptoms_collected)}\n"
    
    # Get first user message (usually the chief complaint)
    user_messages = [m for m in st.session_state.messages if m['role'] == 'user']
    if user_messages:
        summary += f"Initial Complaint: {user_messages[0]['content'][:100]}...\n"
    
    return summary

def display_memory_indicator():
    """Display indicator showing AI is remembering the conversation"""
    if len(st.session_state.messages) > 2:
        st.markdown("""
        <div class="info-box">
            <strong>🧠 Memory Active:</strong> Dr. Elysian remembers all {count} messages in this consultation.
        </div>
        """.format(count=len(st.session_state.messages)), unsafe_allow_html=True)

# Run the app
if __name__ == "__main__":
    initialize_session_state()

    if st.session_state.get('locked_out', False):
        st.error("Application locked. Access denied.")
        st.stop()

    if not st.session_state.get('logged_in', False):
        login_page()
    else:
        # Show memory indicator
        if 'messages' in st.session_state and len(st.session_state.messages) > 2:
            with st.sidebar:
                st.markdown("---")
                display_memory_indicator()
        
        main()
