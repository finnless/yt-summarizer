import streamlit as st
from summarizer import Summarizer

def initialize_components():
    """Initialize summarizer and messages."""
    if "summarizer" not in st.session_state:
        st.session_state.summarizer = Summarizer()

    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

def handle_message(msg):
    """Handle a message in the chat interface."""
    st.chat_message(msg["role"]).write(msg["content"])

    if 'source' in msg:
        start = 0 if msg['source']['start'] == 'TEST' else int(msg['source']['start'])
        print('start1=', start)
        with st.expander('Source'):
            st.video(f"https://www.youtube.com/watch?v={msg['source']['video_id']}", start_time=start)

# Set page configuration
st.set_page_config(page_title="YouTube Video Summarizer", page_icon='📺')

st.title("YouTube Video Summarizer")

# Initialize chat and summarizer
initialize_components()

# Handle every message in the session
for msg in st.session_state.messages:
    handle_message(msg)

if prompt := st.chat_input(placeholder=""):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        result = st.session_state.summarizer.new_query(st.session_state.messages)
        response = result['answer']

        st.write(response)

        if 'source_documents' in result:
            metadata = result['source_documents'][0].metadata
            # print('metadata=\n', metadata)
            st.session_state.messages.append({"role": "assistant", "content": response, "source": metadata})
            start = 0 if metadata['start'] == 'TEST' else int(metadata['start'])
            print('start2=', start)
            with st.expander('Source'):
                st.video(f"https://www.youtube.com/watch?v={metadata['video_id']}", start_time=start)
        else:
            st.session_state.messages.append({"role": "assistant", "content": response})

