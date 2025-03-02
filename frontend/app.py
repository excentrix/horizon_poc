# frontend/app.py
import streamlit as st
import asyncio
import sys
import os
from datetime import datetime
import json

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.mentor import MentorService
from app.services.memory import MemoryService
from app.models.student import Student

# Initialize services
memory_service = MemoryService()
mentor_service = MentorService()

# Page configuration
st.set_page_config(
    page_title="AI Student Mentor",
    page_icon="🎓",
    layout="wide"
)

# Session state initialization
if "student_id" not in st.session_state:
    st.session_state.student_id = None
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Login/Registration section
if not st.session_state.student_id:
    st.title("🎓 AI Student Mentor")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                # For Phase 1, we'll use a simple lookup
                # In a real app, we'd authenticate properly
                student = asyncio.run(memory_service.get_student_by_email(email))
                if student:
                    st.session_state.student_id = student["_id"]
                    st.rerun()
                else:
                    st.error("Student not found")
    
    with tab2:
        with st.form("signup_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            university = st.text_input("University (Optional)")
            program = st.text_input("Program/Major (Optional)")
            year = st.selectbox("Year", [1, 2, 3, 4, "Graduate"])
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign Up")
            
            if submitted:
                # Create new student
                student = Student(
                    name=name,
                    email=email,
                    university=university if university else None,
                    program=program if program else None,
                    year=year if isinstance(year, int) else None
                )
                
                # Save student (in real app, we'd hash the password)
                student_id = asyncio.run(memory_service.create_student(student))
                st.session_state.student_id = student_id
                st.success("Account created successfully!")
                st.rerun()

# Main mentor interface
else:
    # Layout with two columns
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("🎓 AI Student Mentor")
        
        # Get student information
        student = asyncio.run(memory_service.get_student(st.session_state.student_id))
        if student:
            st.write(f"Welcome back, {student.get('name', 'Student')}!")
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Input for new message
        prompt = st.chat_input("How can I help you today?")
        if prompt:
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Display assistant response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                # Define full_response in this scope before using it in the nested function
                full_response = ""
                
                # Call mentor service to get response
                async def get_response():
                    global full_response
                    conversation_id = st.session_state.conversation_id
                    
                    # Get streaming response
                    async for response_chunk in mentor_service.respond_to_student(
                        st.session_state.student_id,
                        prompt,
                        conversation_id
                    ):
                        # Check if this is our special end token with conversation ID
                        if response_chunk.startswith("<CONVERSATION_ID>"):
                            # Extract conversation ID
                            conv_id = response_chunk.replace("<CONVERSATION_ID>", "").replace("</CONVERSATION_ID>", "")
                            if not st.session_state.conversation_id:
                                st.session_state.conversation_id = conv_id
                        else:
                            # Regular token
                            full_response += response_chunk
                            message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                
                # Run asynchronous code
                asyncio.run(get_response())
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    # Student information sidebar
    with col2:
        st.subheader("Student Profile")
        if student:
            st.write(f"**Name:** {student.get('name', 'N/A')}")
            st.write(f"**Email:** {student.get('email', 'N/A')}")
            st.write(f"**University:** {student.get('university', 'N/A')}")
            st.write(f"**Program:** {student.get('program', 'N/A')}")
            st.write(f"**Year:** {student.get('year', 'N/A')}")
            
            # Show extracted facts (if any)
            if "facts" in student and student["facts"]:
                st.subheader("What I Know About You")
                
                # Academic facts
                if "academic" in student["facts"] and student["facts"]["academic"]:
                    st.write("**Academic**")
                    for key, value in student["facts"]["academic"].items():
                        if isinstance(value, dict) and "value" in value:
                            st.write(f"- {key.replace('_', ' ').title()}: {value['value']}")
                        else:
                            st.write(f"- {key.replace('_', ' ').title()}: {value}")
                
                # Career facts
                if "career" in student["facts"] and student["facts"]["career"]:
                    st.write("**Career**")
                    for key, value in student["facts"]["career"].items():
                        if isinstance(value, dict) and "value" in value:
                            st.write(f"- {key.replace('_', ' ').title()}: {value['value']}")
                        else:
                            st.write(f"- {key.replace('_', ' ').title()}: {value}")
                
                # Personal facts
                if "personal" in student["facts"] and student["facts"]["personal"]:
                    st.write("**Personal**")
                    for key, value in student["facts"]["personal"].items():
                        if isinstance(value, dict) and "value" in value:
                            st.write(f"- {key.replace('_', ' ').title()}: {value['value']}")
                        else:
                            st.write(f"- {key.replace('_', ' ').title()}: {value}")