from langchain.schema import ChatMessage
from langchain.callbacks.base import BaseCallbackHandler

from summarizer import Summarizer

import streamlit as st
import os


class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)



st.set_page_config(page_title="YouTube Video Summarizer", page_icon='📺')

st.title("YouTube Video Summarizer")

# Create instance of Summarizer
if 'summarizer' not in st.session_state:
    st.session_state.summarizer = Summarizer()

# Chat interface
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])
    if 'source' in msg:
        # Check if sourcing whole video summary
        if msg['source']['start'] == 'TEST':
            start = 0
        else:
            start = int(msg['source']['start'])
        with st.expander('Source'):
            st.video(f"https://www.youtube.com/watch?v={msg['source']['video_id']}", start_time=start)



if prompt := st.chat_input(placeholder=""):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        stream_handler = StreamHandler(st.empty())
        result = st.session_state.summarizer.new_query(st.session_state.messages)
        response = result['answer']
        if 'source_documents' in result:
            metadata = result['source_documents'][0].metadata
            print('metadata=\n', metadata)
            st.session_state.messages.append({"role": "assistant", "content": response, "source": metadata})
            st.write(response)
            # Check if sourcing whole video summary
            if metadata['start'] == 'TEST':
                start = 0
            else:
                start = int(metadata['start'])
            with st.expander('Source'):
                st.video(f"https://www.youtube.com/watch?v={metadata['video_id']}", start_time=start)
        else:
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.write(response)

