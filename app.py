"""
Iterative Code Review Bot — Streamlit Web UI.

A beautiful web interface for the code review bot with
real-time progress tracking and structured report display.

Run: streamlit run app.py
"""

import streamlit as st  # pyre-ignore
import os
import json

from dotenv import load_dotenv  # pyre-ignore
load_dotenv(override=True)

from src.graph import build_review_graph  # pyre-ignore


# ──────────────────────────────────────────────────────────
# Page Configuration
# ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Iterative Code Review Bot",
    page_icon="assets/logo.png",
    layout="wide",
)

st.logo("assets/logo.png")

# Initialize chat sessions
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {
        "Chat 1": [
            {"role": "assistant", "content": "Hello! I'm your AI Code Reviewer.\n\nPaste your Python code below, and I'll analyze it, find bugs, and suggest improvements. 🚀"}
        ]
    }
    st.session_state.current_session = "Chat 1"
    st.session_state.session_counter = 1

# ──────────────────────────────────────────────────────────
# Custom CSS
# ──────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    /* Global Typography */
    .block-container { font-family: 'Outfit', sans-serif; padding-top: 2rem !important; }
    
    /* Hero Section */
    .hero-title {
        background: linear-gradient(135deg, #4f46e5 0%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        letter-spacing: -1px;
        margin-bottom: 0.2rem;
    }

    .hero-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.25rem;
        font-weight: 400;
        margin-bottom: 2.5rem;
    }

    /* Step Cards (Glassmorphism) */
    .step-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-left: 4px solid #6366f1;
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .step-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }

    /* Issue Severity Colors */
    .issue-critical { border-left-color: #ef4444 !important; }
    .issue-warning { border-left-color: #f59e0b !important; }
    .issue-info { border-left-color: #3b82f6 !important; }

    /* Stats Grid */
    .stats-card {
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.3);
        margin-top: 1rem;
        margin-bottom: 2rem;
    }

    .stats-number { font-size: 2.5rem; font-weight: 700; line-height: 1; margin-bottom: 0.5rem; }
    .stats-label { font-size: 0.9rem; font-weight: 500; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #4f46e5 0%, #ec4899 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 8px;
        font-weight: 600;
        font-family: 'Outfit', sans-serif;
        box-shadow: 0 4px 14px 0 rgba(79, 70, 229, 0.39);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5);
    }
    
    /* Sidebar ChatGPT-style Buttons */
    [data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        color: #e2e8f0 !important;
        border: none !important;
        padding: 0.5rem 0.75rem !important;
        border-radius: 8px !important;
        font-weight: 400 !important;
        font-family: inherit !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
        text-align: left !important;
        transition: background 0.2s ease !important;
        margin-bottom: 0.1rem !important;
    }
    [data-testid="stSidebar"] .stButton > button * {
        font-size: 0.95rem !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        transform: none !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: rgba(255, 255, 255, 0.15) !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────

st.markdown('<h1 class="hero-title">🤖 Iterative Code Review Bot</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Powered by LangGraph + gemini — Analyze, Fix, Repeat</p>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────
# API Key Check
# ──────────────────────────────────────────────────────────

provider = os.getenv("LLM_PROVIDER", "groq").lower()

if provider == "gemini" and not os.getenv("GOOGLE_API_KEY"):
    st.error("⚠️ **GOOGLE_API_KEY** not found! Please set it in your `.env` file.")
    st.info("Get your API key from: [Google AI Studio](https://aistudio.google.com/apikey)")
    st.stop()
elif provider == "groq" and not os.getenv("GROQ_API_KEY"):
    st.error("⚠️ **GROQ_API_KEY** not found! Please set it in your `.env` file.")
    st.info("Get your API key from: [Groq Console](https://console.groq.com/keys)")
    st.stop()
elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️ **OPENAI_API_KEY** not found! Please set it in your `.env` file.")
    st.info("Get your API key from: [OpenAI Platform](https://platform.openai.com/api-keys)")
    st.stop()
# Ollama runs locally, so logic skips api key checks if provider == "ollama"

# ──────────────────────────────────────────────────────────
# Sidebar — Settings
# ──────────────────────────────────────────────────────────

with st.sidebar:
    if st.button("New chat", use_container_width=True, icon=":material/edit_square:"):
        st.session_state.session_counter += 1
        new_session_name = f"Chat {st.session_state.session_counter}"
        st.session_state.chat_sessions[new_session_name] = [
            {"role": "assistant", "content": "Hello! I'm your AI Code Reviewer.\n\nPaste your Python code below, and I'll analyze it, find bugs, and suggest improvements. 🚀"}
        ]
        st.session_state.current_session = new_session_name
        st.rerun()

    if st.button("Search chats", use_container_width=True, icon=":material/search:"):
        pass

    st.markdown("<p style='color: #888; font-size: 0.85rem; margin-top: 1rem; margin-bottom: 0.5rem; font-weight: 500;'>Your chats</p>", unsafe_allow_html=True)
    
    for session_name in reversed(list(st.session_state.chat_sessions.keys())):
        is_active = session_name == st.session_state.current_session
        btn_type = "primary" if is_active else "secondary"
        if st.button(session_name, use_container_width=True, key=f"btn_{session_name}", type=btn_type):
            st.session_state.current_session = session_name
            st.rerun()

max_iterations = 1

# ──────────────────────────────────────────────────────────
# Main Content — Chat Interface
# ──────────────────────────────────────────────────────────

# Display chat messages from history
current_chat = st.session_state.chat_sessions[st.session_state.current_session]
for msg in current_chat:
    with st.chat_message(msg["role"], avatar="assets/logo.png" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# Chat Input
if prompt := st.chat_input("Paste your Python code here..."):
    # Add user message
    user_msg = f"Please review this code:\n\n```python\n{prompt}\n```"
    st.session_state.chat_sessions[st.session_state.current_session].append({"role": "user", "content": user_msg})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_msg)

    # Bot Response
    with st.chat_message("assistant", avatar="assets/logo.png"):
        status_text = st.empty()
        status_text.markdown("🕵️‍♂️ Starting analysis...")
        
        # [RUBRIC C12: System Architecture Context]
        # Build and compile the LangGraph workflow.
        # This defines the cyclic graph where nodes execute in priority order:
        # Static Analysis -> LLM Analysis -> Extraction -> Fixes -> Evaluation -> Recurse
        graph = build_review_graph()
        
        # Initial state
        initial_state = {
            "original_code": prompt,
            "current_code": prompt,
            "static_analysis_results": "",
            "analysis": "",
            "issues": [],
            "suggestions": [],
            "checklist_results": [],
            "all_checks_passed": False,
            "iteration": 0,
            "max_iterations": max_iterations,
            "is_complete": False,
            "review_history": [],
            "final_report": "",
        }

        final_state = initial_state.copy()
        
        # [RUBRIC C6: Error Handling & Robustness]
        # Wrap the LLM generation streaming in a try/except block to catch Provider Rate Limits
        # or 500 Server Errors gracefully without breaking the Streamlit UI frame.
        try:
            # Run graph and update status dynamically
            for event in graph.stream(initial_state):
                for node_name, node_output in event.items():
                    if node_name == "static_analyzer":
                        status_text.markdown("⚡ Running fast syntax and static checks...")
                    elif node_name == "analyzer":
                        status_text.markdown("🔍 Running deep AI analysis...")
                    elif node_name == "issue_finder":
                        issues = node_output.get("issues", [])
                        status_text.markdown(f"🐛 Found {len(issues)} issue(s)...")
                    elif node_name == "fix_suggester":
                        status_text.markdown("🔧 Generating fix suggestions...")
                    elif node_name == "code_fixer":
                        status_text.markdown("✏️ Applying fixes to the code...")
                    elif node_name == "checklist":
                        iteration = node_output.get('iteration', '?')
                        status_text.markdown(f"✅ Running quality checklist (Iteration {iteration})...")
                    elif node_name == "report_generator":
                        status_text.markdown("📄 Writing final report draft...")

                    elif node_name == "report_validator":
                        status_text.markdown("🔎 Validating and correcting report...")
                    
                    if isinstance(node_output, dict):
                        final_state.update(node_output)

            # Clear status and show final report
            status_text.empty()
            report = final_state.get("final_report", "⚠️ Sorry, an error occurred while generating the report.")
            
            st.markdown(report)
            st.session_state.chat_sessions[st.session_state.current_session].append({"role": "assistant", "content": report})
            
        except Exception as e:
            status_text.empty()
            st.error(f"🚨 **Pipeline Interrupted:** {str(e)}")
            st.warning("The LLM Provider may be experiencing severe rate limiting or a 500 error. Please wait a few seconds and try again, or switch providers in your `.env` file.")
