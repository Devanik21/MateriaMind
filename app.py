import streamlit as st
import google.generativeai as genai
from datetime import datetime
import json
import re
from typing import List, Dict, Any
import pandas as pd
from io import StringIO
import base64
from tinydb import TinyDB, Query
import os

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
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    
    .assistant-message {
        background-color: #f3e5f5;
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
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .prescription-header {
        text-align: center;
        color: #333;
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
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    
    .stat-label {
        color: #666;
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

def save_session_to_db(session_id: str, messages: List[Dict], patient_info: Dict, symptoms: List[str]):
    """Save current session to database"""
    sessions = get_sessions_table()
    session_data = {
        'session_id': session_id,
        'messages': messages,
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
    
    # Load from database if exists
    if 'loaded_from_db' not in st.session_state:
        saved_session = load_session_from_db(st.session_state.session_id)
        if saved_session:
            st.session_state.messages = saved_session.get('messages', [])
            st.session_state.patient_info = saved_session.get('patient_info', {})
            st.session_state.symptoms_collected = saved_session.get('symptoms_collected', [])
        st.session_state.loaded_from_db = True

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

# System prompt for the homeopathy doctor
SYSTEM_PROMPT = """You are Dr. HomeoHeal, an experienced and compassionate homeopathic doctor with over 20 years of practice. Your approach is:

1. CONSULTATION PHASE:
   - Greet the patient warmly and professionally
   - Ask about their main complaint/problem
   - Follow up with relevant questions about:
     * Duration and severity of symptoms
     * Any triggering factors
     * Associated symptoms
     * Previous treatments tried
     * Medical history (if relevant)
     * Lifestyle factors (diet, sleep, stress)
     * Mental/emotional state
   - Be empathetic and reassuring
   - Ask one or two focused questions at a time
   - Listen carefully to understand the complete picture
   - REMEMBER ALL INFORMATION shared by the patient throughout the conversation

2. PRESCRIPTION PHASE (only after gathering sufficient information):
   - When you have enough information, indicate you're ready to prescribe by saying "PRESCRIPTION_READY"
   - Provide 3-5 homeopathic remedies in this exact JSON format:
   ```json
   {
     "patient_name": "Patient",
     "date": "current_date",
     "chief_complaint": "main problem",
     "diagnosis": "homeopathic diagnosis",
     "remedies": [
       {
         "medicine": "Medicine Name",
         "potency": "30C or 200C or 1M",
         "dosage": "frequency and duration",
         "instructions": "when to take, how to take",
         "purpose": "what it treats"
       }
     ],
     "dietary_advice": ["advice 1", "advice 2"],
     "lifestyle_recommendations": ["recommendation 1", "recommendation 2"],
     "follow_up": "when to follow up",
     "precautions": ["precaution 1", "precaution 2"]
   }
   ```

3. IMPORTANT GUIDELINES:
   - Only prescribe well-known homeopathic remedies (Arnica, Belladonna, Nux Vomica, Pulsatilla, etc.)
   - Be conservative with potencies (prefer 30C for acute, 200C for chronic)
   - Always include lifestyle and dietary advice
   - Remind about follow-up consultation
   - Never diagnose serious conditions without recommending conventional medical consultation
   - Be professional, ethical, and within homeopathic scope
   - MAINTAIN CONTEXT: Remember everything the patient has told you in this conversation

4. COMMUNICATION STYLE:
   - Warm, professional, and reassuring
   - Use simple language, avoid complex medical jargon
   - Show empathy and understanding
   - Be encouraging and positive
   - Reference previous information shared by the patient to show continuity

Remember: You're here to help through homeopathy, but always prioritize patient safety. Keep the entire conversation in mind when making recommendations."""

def initialize_chat_model():
    """Initialize the chat model and start a persistent chat session"""
    if st.session_state.chat_model is None:
        st.session_state.chat_model = genai.GenerativeModel('gemma-3n-e4b-it')
        
        # Start chat with system prompt
        st.session_state.chat_session = st.session_state.chat_model.start_chat(
            history=[
                {"role": "user", "parts": [SYSTEM_PROMPT]},
                {"role": "model", "parts": ["I understand. I am Dr. HomeoHeal, and I will conduct thorough homeopathic consultations while remembering all information shared throughout our conversation. I'm ready to help patients with compassion and expertise."]}
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

def create_download_link(text: str, filename: str) -> str:
    """Create download link for text content"""
    b64 = base64.b64encode(text.encode()).decode()
    return f'<a href="data:text/markdown;base64,{b64}" download="{filename}" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.5rem 2rem; border-radius: 25px; font-weight: bold; cursor: pointer;">📥 Download Prescription</button></a>'

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
            <div class="message-role">🩺 Dr. HomeoHeal</div>
            <div class="message-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)
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
                    st.session_state.symptoms_collected
                )
                st.success("Session saved!")
        
        with col2:
            if st.button("🔄 New", use_container_width=True):
                # Save current session before starting new
                save_session_to_db(
                    st.session_state.session_id,
                    st.session_state.messages,
                    st.session_state.patient_info,
                    st.session_state.symptoms_collected
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
                        st.session_state.chat_session = None
                        st.session_state.chat_model = None
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
            <h3>👋 Welcome to HomeoClinic AI!</h3>
            <p>I'm Dr. HomeoHeal, your virtual homeopathic doctor. I'll remember everything you tell me throughout our conversation.</p>
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
        st.session_state.symptoms_collected
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
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Markdown download
        md_content = generate_prescription_markdown(prescription)
        st.markdown(
            create_download_link(
                md_content,
                f"prescription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            ),
            unsafe_allow_html=True
        )
    
    with col2:
        # JSON download
        json_content = json.dumps(prescription, indent=2)
        b64 = base64.b64encode(json_content.encode()).decode()
        st.markdown(
            f'<a href="data:application/json;base64,{b64}" download="prescription_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.5rem 2rem; border-radius: 25px; font-weight: bold; cursor: pointer;">📥 Download JSON</button></a>',
            unsafe_allow_html=True
        )
    
    with col3:
        # CSV download (remedies only)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        b64_csv = base64.b64encode(csv_content.encode()).decode()
        st.markdown(
            f'<a href="data:text/csv;base64,{b64_csv}" download="prescription_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.5rem 2rem; border-radius: 25px; font-weight: bold; cursor: pointer;">📥 Download CSV</button></a>',
            unsafe_allow_html=True
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
    # Initialize session state
    initialize_session_state()
    
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
    
    # Chat input
    user_input = st.chat_input("Describe your symptoms or ask a question...")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        st.session_state.total_messages += 1
        
        # Extract symptoms (simple keyword extraction)
        symptom_keywords = ['pain', 'ache', 'fever', 'cough', 'cold', 'headache', 
                           'nausea', 'vomit', 'diarrhea', 'constipation', 'anxiety', 
                           'stress', 'insomnia', 'fatigue', 'weakness', 'dizzy',
                           'swelling', 'rash', 'itch', 'burn', 'cramp', 'sore',
                           'inflammation', 'infection', 'allergy', 'bleeding']
        
        for keyword in symptom_keywords:
            if keyword in user_input.lower() and keyword not in st.session_state.symptoms_collected:
                st.session_state.symptoms_collected.append(keyword)
        
        # Get AI response (using persistent chat session)
        with st.spinner("🩺 Dr. HomeoHeal is thinking..."):
            response = get_ai_response(user_input)
            process_ai_response(response)
        
        # Auto-save after interaction
        save_session_to_db(
            st.session_state.session_id,
            st.session_state.messages,
            st.session_state.patient_info,
            st.session_state.symptoms_collected
        )
        
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
            <strong>🧠 Memory Active:</strong> Dr. HomeoHeal remembers all {count} messages in this conversation.
        </div>
        """.format(count=len(st.session_state.messages)), unsafe_allow_html=True)

# Run the app
if __name__ == "__main__":
    # Show memory indicator
    if 'messages' in st.session_state and len(st.session_state.messages) > 2:
        with st.sidebar:
            st.markdown("---")
            display_memory_indicator()
    
    main()
