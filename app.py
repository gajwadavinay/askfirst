import os
import streamlit as st
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="AskFirst - AI Chat", page_icon="💬", layout="wide")

# Custom CSS for modern dark-themed aesthetics and branding
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1e1e2f 0%, #111119 100%); color: #f5f5f7; }
    .sidebar .sidebar-content { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); }
    h1 { font-family: 'Outfit', sans-serif; font-weight: 700; color: #ffffff; text-shadow: 0 4px 12px rgba(0,0,0,0.5); }
</style>
""", unsafe_allow_html=True)

st.title("💬 AskFirst Chat")

try:
    threads = requests.get(f"{API_URL}/threads").json()
except Exception:
    st.error("Could not connect to backend server. Make sure it is running on port 8000.")
    st.stop()

# Sidebar: Manage and select conversation threads
with st.sidebar:
    st.header("🗂️ Conversations")
    
    # New Thread form
    with st.form("new_thread_form", clear_on_submit=True):
        new_thread_name = st.text_input("New Thread Name", placeholder="Enter thread topic...")
        submitted = st.form_submit_button("➕ Create Thread", use_container_width=True)
        if submitted and new_thread_name.strip():
            response = requests.post(f"{API_URL}/threads", json={"name": new_thread_name.strip()})
            if response.status_code == 201:
                st.success("Created!")
                st.rerun()

    st.markdown("---")
    
    if not threads:
        st.info("No active threads. Create one above!")
        selected_thread_id = None
    else:
        # Keep track of active thread using st.session_state to persist selectbox selection
        thread_opts = {t["id"]: t["name"] for t in threads}
        if "active_thread_id" not in st.session_state or st.session_state.active_thread_id not in thread_opts:
            st.session_state.active_thread_id = list(thread_opts.keys())[0]
            
        selected_thread_id = st.selectbox(
            "Select Thread", 
            options=list(thread_opts.keys()), 
            format_func=lambda x: thread_opts[x],
            index=list(thread_opts.keys()).index(st.session_state.active_thread_id)
        )
        st.session_state.active_thread_id = selected_thread_id
        
        # Option to delete the currently selected thread
        if st.button("🗑️ Delete Current Thread", type="secondary", use_container_width=True):
            requests.delete(f"{API_URL}/threads/{selected_thread_id}")
            st.session_state.active_thread_id = None
            st.rerun()

# Main area: chat logs and query interface
if selected_thread_id:
    # Retrieve messages for the current thread
    messages = requests.get(f"{API_URL}/threads/{selected_thread_id}/messages").json()
    
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input box positioned at the bottom of the page
    user_input = st.chat_input("Ask a question...")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
            
        with st.spinner("Thinking..."):
            response = requests.post(
                f"{API_URL}/threads/{selected_thread_id}/chat", 
                json={"content": user_input}
            )
            if response.status_code == 200:
                st.rerun()  # Rerun Streamlit script to fetch and show the LLM reply
            else:
                st.error("Error communicating with LLM service.")
else:
    st.info("👈 Please create or select a conversation thread in the sidebar to start chatting.")
