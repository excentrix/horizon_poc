# # frontend/app.py
# import streamlit as st

# # Page configuration MUST be the first Streamlit command
# st.set_page_config(
#     page_title="AI Student Mentor",
#     page_icon="🎓",
#     layout="wide"
# )

# import asyncio
# import sys
# import os
# from datetime import datetime
# import json
# from bson.objectid import ObjectId  # Add this import

# # Add the project root to the path
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from app.services.mentor import MentorService
# from app.services.memory import MemoryService
# from app.models.student import Student
# from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# # Initialize services - ONLY ONCE at the module level
# @st.cache_resource
# def get_services():
#     return {
#         "memory_service": MemoryService(),
#         "mentor_service": MentorService()
#     }

# services = get_services()
# memory_service = services["memory_service"]
# mentor_service = services["mentor_service"]

# # Session state initialization - DO NOT USE st.rerun() here
# if "student_id" not in st.session_state:
#     st.session_state.student_id = None
# if "conversation_id" not in st.session_state:
#     st.session_state.conversation_id = None
# if "messages" not in st.session_state:
#     st.session_state.messages = []
# if "debug" not in st.session_state:
#     st.session_state.debug = False

# # Login function - separate function to avoid multiple reruns
# def handle_login(email, password):
#     student = asyncio.run(memory_service.get_student_by_email(email))
#     if student:
#         st.session_state.student_id = str(student["_id"])  # Ensure ID is a string
#         st.session_state.logged_in = True
#         return True
#     return False

# # Registration function
# def handle_registration(name, email, university, program, year, password):
#     student = Student(
#         name=name,
#         email=email,
#         university=university if university else None,
#         program=program if program else None,
#         year=year if isinstance(year, int) else None
#     )
    
#     student_id = asyncio.run(memory_service.create_student(student))
#     st.session_state.student_id = student_id
#     st.session_state.logged_in = True
#     return True

# # Function to load conversation history
# def load_conversation_history(student_id):
#     # Get the student's conversation using the get_or_create method
#     conversation_id = asyncio.run(
#         memory_service.get_or_create_student_conversation(student_id)
#     )
    
#     # Store the conversation ID in session state
#     st.session_state.conversation_id = conversation_id
    
#     # Get message history
#     message_history = memory_service.get_message_history(conversation_id)
    
#     # Convert to format for session state
#     messages = []
#     for msg in message_history.messages:
#         # Skip system messages in the UI display
#         if isinstance(msg, SystemMessage):
#             continue
        
#         # Determine role based on message type
#         if isinstance(msg, HumanMessage):
#             role = "user"
#         else:
#             role = "assistant"
            
#         # Add to messages list
#         messages.append({
#             "role": role,
#             "content": msg.content
#         })
    
#     return messages, conversation_id

# # Main application logic
# if not st.session_state.student_id:
#     st.title("🎓 AI Student Mentor")
    
#     tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
#     with tab1:
#         with st.form("login_form"):
#             email = st.text_input("Email")
#             password = st.text_input("Password", type="password")
#             submitted = st.form_submit_button("Login")
            
#             if submitted:
#                 if handle_login(email, password):
#                     # DO NOT use st.rerun() here - instead, set a flag
#                     st.success("Login successful!")
#                     # Just reload the page naturally
#                 else:
#                     st.error("Student not found")
    
#     with tab2:
#         with st.form("signup_form"):
#             name = st.text_input("Full Name")
#             email = st.text_input("Email")
#             university = st.text_input("University (Optional)")
#             program = st.text_input("Program/Major (Optional)")
#             year = st.selectbox("Year", [1, 2, 3, 4, "Graduate"])
#             password = st.text_input("Password", type="password")
#             submitted = st.form_submit_button("Sign Up")
            
#             if submitted:
#                 if handle_registration(name, email, university, program, year, password):
#                     st.success("Account created successfully!")
#                     # DO NOT use st.rerun() here
# else:
#     # If user is logged in but has no messages yet, load them
#     if len(st.session_state.messages) == 0:
#         try:
#             st.session_state.messages, conversation_id = load_conversation_history(st.session_state.student_id)
#             st.session_state.debug = True
#         except Exception as e:
#             st.error(f"Error loading conversation history: {str(e)}")
    
#     # Layout with two columns
#     col1, col2 = st.columns([3, 1])
    
#     with col1:
#         st.title("🎓 AI Student Mentor")
        
#         # Get student information
#         student = asyncio.run(memory_service.get_student(st.session_state.student_id))
#         if student:
#             st.write(f"Welcome back, {student.get('name', 'Student')}!")
        
#         # Display chat messages
#         for message in st.session_state.messages:
#             with st.chat_message(message["role"]):
#                 st.markdown(message["content"])
        
#         # Input for new message
#         prompt = st.chat_input("How can I help you today?")
#         if prompt:
#             # Add user message to chat
#             st.session_state.messages.append({"role": "user", "content": prompt})
            
#             # Display user message
#             with st.chat_message("user"):
#                 st.markdown(prompt)
            
#             # Display assistant response
#             with st.chat_message("assistant"):
#                 message_placeholder = st.empty()
                
#                 # Call mentor service to get response
#                 async def get_response():
#                     full_text = ""
#                     conversation_id = st.session_state.conversation_id
                    
#                     # Get streaming response
#                     async for response_chunk in mentor_service.respond_to_student(
#                         st.session_state.student_id,
#                         prompt,
#                         conversation_id
#                     ):
#                         # Check if this is our special end token with conversation ID
#                         if response_chunk.startswith("<CONVERSATION_ID>"):
#                             # Extract conversation ID
#                             conv_id = response_chunk.replace("<CONVERSATION_ID>", "").replace("</CONVERSATION_ID>", "")
#                             st.session_state.conversation_id = conv_id
#                         else:
#                             # Regular token
#                             full_text += response_chunk
#                             message_placeholder.markdown(full_text + "▌")
                    
#                     message_placeholder.markdown(full_text)
#                     return full_text
                
#                 # Run asynchronous code and get the full response
#                 full_response = asyncio.run(get_response())
                
#                 # Add assistant response to chat history
#                 st.session_state.messages.append({"role": "assistant", "content": full_response})
    
#     # Student information sidebar
#     with col2:
#         st.subheader("Student Profile")
#         if student:
#             st.write(f"**Name:** {student.get('name', 'N/A')}")
#             st.write(f"**Email:** {student.get('email', 'N/A')}")
#             st.write(f"**University:** {student.get('university', 'N/A')}")
#             st.write(f"**Program:** {student.get('program', 'N/A')}")
#             st.write(f"**Year:** {student.get('year', 'N/A')}")
            
#             # Debug information 
#             if st.session_state.debug:
#                 with st.expander("Debug Info"):
#                     st.write(f"Conversation ID: {st.session_state.conversation_id}")
#                     st.write(f"Student ID: {st.session_state.student_id}")
#                     st.write(f"UI Message count: {len(st.session_state.messages)}")
                    
#                     # Verify the conversation exists directly in MongoDB
#                     try:
#                         from pymongo import MongoClient
#                         from app.config import MONGODB_URI, MONGODB_DB
#                         client = MongoClient(MONGODB_URI)
#                         db = client[MONGODB_DB]
                        
#                         # Check if the conversation exists by ID
#                         conv_obj_id = ObjectId(st.session_state.conversation_id)
#                         conv = db.conversations.find_one({"_id": conv_obj_id})
                        
#                         if conv:
#                             st.write("✅ Conversation found in database")
#                             st.write(f"Student ID in DB: {conv.get('student_id')}")
#                             st.write(f"Created: {conv.get('created_at')}")
                            
#                             # Count messages in this conversation
#                             msg_count = db.conversations.count_documents({"session_id": st.session_state.conversation_id})
#                             st.write(f"DB Message documents: {msg_count}")
#                         else:
#                             st.write("❌ Conversation NOT found in database!")
#                     except Exception as e:
#                         st.write(f"Error checking database: {str(e)}")
                    
#                     # Button to reload messages from DB
#                     if st.button("Reload Messages from DB"):
#                         st.session_state.messages, _ = load_conversation_history(st.session_state.student_id)
#                         st.experimental_rerun()
                        
#                     # Button to clear session
#                     if st.button("Log Out"):
#                         for key in list(st.session_state.keys()):
#                             del st.session_state[key]
#                         st.experimental_rerun()
            
#             # Show extracted facts (if any)
#             if "facts" in student and student["facts"]:
#                 st.subheader("What I Know About You")
                
#                 # Academic facts
#                 if "academic" in student["facts"] and student["facts"]["academic"]:
#                     st.write("**Academic**")
#                     for key, value in student["facts"]["academic"].items():
#                         if isinstance(value, dict) and "value" in value:
#                             st.write(f"- {key.replace('_', ' ').title()}: {value['value']}")
#                         else:
#                             st.write(f"- {key.replace('_', ' ').title()}: {value}")
                
#                 # Career facts
#                 if "career" in student["facts"] and student["facts"]["career"]:
#                     st.write("**Career**")
#                     for key, value in student["facts"]["career"].items():
#                         if isinstance(value, dict) and "value" in value:
#                             st.write(f"- {key.replace('_', ' ').title()}: {value['value']}")
#                         else:
#                             st.write(f"- {key.replace('_', ' ').title()}: {value}")
                
#                 # Personal facts
#                 if "personal" in student["facts"] and student["facts"]["personal"]:
#                     st.write("**Personal**")
#                     for key, value in student["facts"]["personal"].items():
#                         if isinstance(value, dict) and "value" in value:
#                             st.write(f"- {key.replace('_', ' ').title()}: {value['value']}")
#                         else:
#                             st.write(f"- {key.replace('_', ' ').title()}: {value}")

# frontend/app.py
import streamlit as st

# Page configuration MUST be the first Streamlit command
st.set_page_config(
    page_title="AI Student Mentor",
    page_icon="🎓",
    layout="wide"
)

import asyncio
import sys
import os
from datetime import datetime
import json
from bson.objectid import ObjectId  # Add this import

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.mentor import MentorService
from app.services.memory import MemoryService
from app.models.student import Student
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Initialize services - ONLY ONCE at the module level
@st.cache_resource
def get_services():
    return {
        "memory_service": MemoryService(),
        "mentor_service": MentorService()
    }

services = get_services()
memory_service = services["memory_service"]
mentor_service = services["mentor_service"]

# Session state initialization
if "student_id" not in st.session_state:
    st.session_state.student_id = None
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "debug" not in st.session_state:
    st.session_state.debug = True  # Enable debug by default

# Function to get student data safely
async def get_student_data(student_id):
    try:
        # Make sure student_id is a string
        student_id_str = str(student_id)
        
        # Try to get the student data
        student = await memory_service.get_student(student_id_str)
        
        if not student:
            # If that fails, try with ObjectId conversion
            student = await memory_service.get_student(ObjectId(student_id_str))
        
        return student
    except Exception as e:
        st.sidebar.error(f"Error retrieving student data: {str(e)}")
        print(f"Error retrieving student: {str(e)}")
        return None

# Login function - separate function to avoid multiple reruns
def handle_login(email, password):
    student = asyncio.run(memory_service.get_student_by_email(email))
    if student:
        st.session_state.student_id = str(student["_id"])  # Ensure ID is a string
        st.session_state.student_name = student.get("name", "Student")  # Cache name
        st.session_state.student_email = student.get("email", "")  # Cache email
        st.session_state.logged_in = True
        return True
    return False

# Registration function
def handle_registration(name, email, university, program, year, password):
    student = Student(
        name=name,
        email=email,
        university=university if university else None,
        program=program if program else None,
        year=year if isinstance(year, int) else None
    )
    
    student_id = asyncio.run(memory_service.create_student(student))
    st.session_state.student_id = student_id
    st.session_state.student_name = name  # Cache name
    st.session_state.student_email = email  # Cache email
    st.session_state.logged_in = True
    return True

# Function to load conversation history
def load_conversation_history(student_id):
    # Get the student's conversation using the get_or_create method
    conversation_id = asyncio.run(
        memory_service.get_or_create_student_conversation(student_id)
    )
    
    # Store the conversation ID in session state
    st.session_state.conversation_id = conversation_id
    
    # Get message history
    message_history = memory_service.get_message_history(conversation_id)
    
    # Convert to format for session state
    messages = []
    for msg in message_history.messages:
        # Skip system messages in the UI display
        if isinstance(msg, SystemMessage):
            continue
        
        # Determine role based on message type
        if isinstance(msg, HumanMessage):
            role = "user"
        else:
            role = "assistant"
            
        # Add to messages list
        messages.append({
            "role": role,
            "content": msg.content
        })
    
    return messages, conversation_id

# Main application logic
if not st.session_state.student_id:
    st.title("🎓 AI Student Mentor")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if handle_login(email, password):
                    st.success("Login successful!")
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
                if handle_registration(name, email, university, program, year, password):
                    st.success("Account created successfully!")
else:
    # If user is logged in but has no messages yet, load them
    if len(st.session_state.messages) == 0:
        try:
            st.session_state.messages, conversation_id = load_conversation_history(st.session_state.student_id)
        except Exception as e:
            st.error(f"Error loading conversation history: {str(e)}")
    
    # Retrieve student data using the safer function
    student = asyncio.run(get_student_data(st.session_state.student_id))
    
    # Layout with two columns
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("🎓 AI Student Mentor")
        
        # Welcome message - use cached name if possible
        student_name = student.get("name", "") if student else st.session_state.get("student_name", "Student")
        st.write(f"Welcome back, {student_name}!")
        
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
                
                # Call mentor service to get response
                async def get_response():
                    full_text = ""
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
                            st.session_state.conversation_id = conv_id
                        else:
                            # Regular token
                            full_text += response_chunk
                            message_placeholder.markdown(full_text + "▌")
                    
                    message_placeholder.markdown(full_text)
                    return full_text
                
                # Run asynchronous code and get the full response
                full_response = asyncio.run(get_response())
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    # Student information sidebar
    with col2:
        st.subheader("Student Profile")
        
        # Attempt to use either retrieved student data or cached info
        if student:
            st.write(f"**Name:** {student.get('name', 'N/A')}")
            st.write(f"**Email:** {student.get('email', 'N/A')}")
            st.write(f"**University:** {student.get('university', 'N/A')}")
            st.write(f"**Program:** {student.get('program', 'N/A')}")
            st.write(f"**Year:** {student.get('year', 'N/A')}")
        else:
            # Fallback to session state if available
            st.write(f"**Name:** {st.session_state.get('student_name', 'N/A')}")
            st.write(f"**Email:** {st.session_state.get('student_email', 'N/A')}")
            
            # Debug info for student retrieval issues
            if st.session_state.debug:
                st.warning("Student data couldn't be retrieved from database")
        
        # Debug information 
        if st.session_state.debug:
            with st.expander("Debug Info"):
                st.write(f"Conversation ID: {st.session_state.conversation_id}")
                st.write(f"Student ID: {st.session_state.student_id}")
                st.write(f"UI Message count: {len(st.session_state.messages)}")
                
                # Add debug info about student retrieval
                if student:
                    st.write("✅ Student data successfully retrieved")
                    st.write(f"Student document keys: {', '.join(student.keys())}")
                else:
                    st.write("❌ Student data retrieval failed")
                
                # Verify the conversation exists directly in MongoDB
                try:
                    from pymongo import MongoClient
                    from app.config import MONGODB_URI, MONGODB_DB
                    client = MongoClient(MONGODB_URI)
                    db = client[MONGODB_DB]
                    
                    # Check if the student exists by ID
                    try:
                        student_obj_id = ObjectId(st.session_state.student_id)
                        db_student = db.students.find_one({"_id": student_obj_id})
                        if db_student:
                            st.write("✅ Student record found directly in database")
                            st.write(f"DB Student name: {db_student.get('name')}")
                            st.write(f"DB Student email: {db_student.get('email')}")
                        else:
                            st.write("❌ Student NOT found directly in database!")
                    except Exception as e:
                        st.write(f"Error checking student in database: {str(e)}")
                    
                    # Check if the conversation exists by ID
                    if st.session_state.conversation_id:
                        try:
                            conv_obj_id = ObjectId(st.session_state.conversation_id)
                            conv = db.conversations.find_one({"_id": conv_obj_id})
                            
                            if conv:
                                st.write("✅ Conversation found in database")
                                st.write(f"Student ID in DB: {conv.get('student_id')}")
                                st.write(f"Created: {conv.get('created_at')}")
                                
                                # Count messages in this conversation
                                msg_count = db.messages.count_documents({"conversation_id": st.session_state.conversation_id})
                                st.write(f"DB Message documents: {msg_count}")
                            else:
                                st.write("❌ Conversation NOT found in database!")
                        except Exception as e:
                            st.write(f"Error checking conversation: {str(e)}")
                except Exception as e:
                    st.write(f"Error connecting to database: {str(e)}")
                
                # Button to reload messages from DB
                if st.button("Reload Messages from DB"):
                    st.session_state.messages, _ = load_conversation_history(st.session_state.student_id)
                    st.experimental_rerun()
                    
                # Button to clear session
                if st.button("Log Out"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.experimental_rerun()
        
        # Show extracted facts (if any)
        if student and "facts" in student and student["facts"]:
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