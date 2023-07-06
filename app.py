import streamlit as st

st.title("YouTube Video Summarizer")

url = st.text_input('Video url', 'https://youtu.be/rn_8GXNN7_Q')

if url:
    st.video(url) 
