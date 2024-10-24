import os
import io
import requests
import streamlit as st
from dotenv import load_dotenv
import PyPDF2
import re
import pandas as pd
from fuzzywuzzy import fuzz
from collections import Counter

# Set Streamlit page config at the very beginning
st.set_page_config(page_title="HireAi")  # Correct placement at the start of the code

# Load environment variables
load_dotenv()

def input_pdf_setup(uploaded_files):
    all_texts = []
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            try:
                pdf_bytes = uploaded_file.read()
                with io.BytesIO(pdf_bytes) as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    all_texts.append(text)
            except Exception as e:
                st.error(f"Error processing PDF: {e}")
                return None
    return all_texts

# Enhanced extraction function to get name, phone, email, location, degree, and college
def extract_personal_info(pdf_text):
    name_regex = re.compile(r"\b[A-Z][a-z]*\s[A-Z][a-z]*\b")  # Example: "First Last"
    phone_regex = re.compile(r"(\+?\d{1,2}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
    email_regex = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    location_regex = re.compile(r"(?:Noida|Delhi|Bangalore|Mumbai|India|Uttar Pradesh|Russia|Moscow|Ghaziabad|Indore|other locations)")
    degree_regex = re.compile(r"\b(B\.?Tech|M\.?Tech|BCA|MCA|BSc|Bachelors|Masters|Higher Secondary)\b", re.IGNORECASE)
    college_regex = re.compile(r"\b(IIT|NIT|GLA|IMS|IGNOU|Lomonosov|other universities)\b")

    name = name_regex.search(pdf_text)
    phone = phone_regex.search(pdf_text)
    email = email_regex.search(pdf_text)
    location = location_regex.search(pdf_text)
    degree = degree_regex.findall(pdf_text)
    college = college_regex.findall(pdf_text)
    
    return {
        "Name": name.group(0) if name else "Not found",
        "Phone": phone.group(0) if phone else "Not found",
        "Email": email.group(0) if email else "Not found",
        "Location": location.group(0) if location else "Not found",
        "Degree": degree if degree else ["Not found"],
        "College": college if college else ["Not found"]
    }

# Enhanced skill extraction based on fuzzy matching
def extract_skills(pdf_text, job_description_skills):
    skill_keywords = [
        "Python", "Java", "C++", "Machine Learning", "Data Analysis", "Project Management", 
        "Leadership", "SQL", "TensorFlow", "Keras", "AWS", "Docker", "Kubernetes", "React", 
        "Angular", "Flask", "Django", "JavaScript", "HTML", "CSS", "Communication", 
        "Problem Solving", "Teamwork", "Agile", "Scrum"
    ]
    
    found_skills = [skill for skill in skill_keywords if re.search(rf'\b{re.escape(skill)}\b', pdf_text, re.IGNORECASE)]
    
    # Fuzzy matching to catch variations of skills mentioned in the job description
    matched_skills = []
    for skill in found_skills:
        for jd_skill in job_description_skills:
            if fuzz.partial_ratio(skill.lower(), jd_skill.lower()) > 80:
                matched_skills.append(skill)
    
    return matched_skills if matched_skills else ["No relevant skills found"]

# Analyze the job description to extract key skills
def extract_job_description_skills(job_description):
    job_keywords = re.findall(r'\b[A-Za-z]+\b', job_description)  # Basic word matching
    job_keywords = [word for word in job_keywords if len(word) > 1]  # Filter short words
    return job_keywords

# Shortlisting and ranking candidates based on job description and resume match
def handle_job_description_and_resume(input_text, pdf_texts, num_candidates):
    if not input_text:
        st.error("Please provide a job description before submitting.")
        return

    job_description_skills = extract_job_description_skills(input_text)
    shortlisted_candidates = []

    for idx, pdf_text in enumerate(pdf_texts):
        personal_info = extract_personal_info(pdf_text)
        skills = extract_skills(pdf_text, job_description_skills)
        
        # Count number of skills matched to rank candidates
        skill_match_count = len([skill for skill in skills if skill in job_description_skills])
        
        shortlisted_candidates.append({
            "Name": personal_info["Name"],
            "Email": personal_info["Email"],
            "Phone": personal_info["Phone"],
            "Location": personal_info["Location"],
            "Degree": ', '.join(personal_info["Degree"]),
            "College": ', '.join(personal_info["College"]),
            "Skills": ', '.join(skills),
            "Skill Matches": skill_match_count
        })

    # Sort candidates by the number of skills matched (descending)
    shortlisted_candidates = sorted(shortlisted_candidates, key=lambda x: x["Skill Matches"], reverse=True)

    # Limit the number of shortlisted candidates to the specified number
    shortlisted_candidates = shortlisted_candidates[:num_candidates]

    # Create and display the table of shortlisted candidates with their details and skills
    if shortlisted_candidates:
        st.subheader("Shortlisted Candidates")
        candidates_df = pd.DataFrame(shortlisted_candidates).drop(columns="Skill Matches")  # Removing the match count from display
        st.write(candidates_df)

# Streamlit App
st.header("HireAi")

# Input for job description
input_text = st.text_area("Job Description: ", key="input")

# File uploader for resumes (multiple PDF files)
uploaded_files = st.file_uploader("Upload resumes (PDF)...", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    st.write(f"{len(uploaded_files)} PDF(s) uploaded successfully")

# Input for number of candidates to hire
num_candidates = st.number_input("Number of candidates to hire:", min_value=1, value=1)

# Button to submit and display shortlisted candidates and skills
submit1 = st.button("Tell Me About the Resume")

# Check for 'Tell Me About the Resume' button submission
if submit1:
    if uploaded_files:
        pdf_texts = input_pdf_setup(uploaded_files)
        handle_job_description_and_resume(input_text, pdf_texts, num_candidates)

# Additional CSV functionality
def chat_with_csv(csv_file):
    if csv_file is not None:
        try:
            df = pd.read_csv(csv_file)
            st.write("Here's your CSV data:")
            st.write(df)

            query = st.text_input("Ask a question about the candidates:")
            if st.button("Submit Query"):
                if "years" in query.lower():
                    experience_column = "Experience"
                    years_required = re.search(r'\d+', query)
                    if years_required:
                        years_required = int(years_required.group())
                        filtered_df = df[df[experience_column] >= years_required]
                        st.write(f"Candidates with {years_required}+ years of experience:")
                        st.write(filtered_df)
                    else:
                        st.write("Could not parse the number of years. Please enter a valid query.")
                else:
                    st.write("Query not recognized. Try asking for 'years of experience'.")
        except Exception as e:
            st.error(f"Error processing CSV: {e}")

# Streamlit App
st.subheader("Chat with your CSV")
csv_file = st.file_uploader("Upload CSV file (optional)", type=["csv"])
submit2 = st.button("Chat with CSV")

if submit2 and csv_file:
    chat_with_csv(csv_file)
