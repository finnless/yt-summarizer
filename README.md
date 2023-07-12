<div align="center">
  <div id="user-content-toc">
    <ul>
      <summary><h1 style="display: inline-block;">🦜️🔗📺 yt-summarizer</h1></summary>
    </ul>
  </div>
</div>
<div align="center">
      <a href="https://yt-summarizer-chat.streamlit.app/"><img src="https://static.streamlit.io/badges/streamlit_badge_black_white.svg"/></a>
      <img src="https://img.shields.io/github/stars/finnless/yt-summarizer?color=blue&style=social"/>
</div>
<br>
A langchain summarizer for YouTube videos using StreamLit, the OpenAI API, and LangChain.

## Usage
You may paste one or more youtube urls into the StreamLit interface.
Here are some great examples: https://www.youtube.com/watch?v=rn_8GXNN7_Q, https://www.youtube.com/watch?v=KMOV1Zy8YeM

Those videos captions' get indexed and stored in a vector database. You may then have a conversation with the chat bot about the contents of the video. The chatbot conveniently embeds the source video starting at the time the relevant information is spoken.

## Technical Description
### Web Application (`app.py`)
- This part of the application is a Streamlit web app called. It requests for OpenAI API Key from the user through a sidebar, confirming that the operation continues only when the key is provided.
- The web application has a chat interface to handle interactions with the end user, and leverages Streamlit session state to maintain the chat history.
- After receiving a message from the user, the application forwards it to the Summarizer's new_query function to provide the reply.
- If the reply includes a source video (i.e., its metadata), the video is shown in the chat interface. This usually happens when the assistant is summarizing the video or referring to a specific part of it.
### Summarizer (`summarizer.py`)
- The Summarizer class defined in the summarizer.py file is the core of the backend logic.
- It initializes with access to three models from OpenAI (GPT-4, GPT-3.5-turbo and GPT-3), and a Chroma vectorstore backed by OpenAI embeddings. This vectorstore serves as a storage structure for semantically indexed documents.
- The class defines methods for conversational retrieval, parsing message history, extracting YouTube video IDs, and more.
- It uses the YouTubeTranscriptApi to retrieve video transcripts given a video ID.
- For new video transcripts, it splits the transcript into manageable chunks and appends these chunks to the Chroma vectorstore.
- Summarization of videos is performed by running a map-reduce type summary chain on the video transcript. The summarized text is added to the vectorstore.
- For each new user query, the summarizer decides whether it should add a new video or answer a question. If video IDs are found in the conversation, it tries to add the video to the Chroma document store. If the video transcript is not available, it will inform the user to try another video. If no video IDs are found, it treats the last user message as a question and tries to answer it. Question answering is performed by using a pre-built conversational retrieval chain.

## Sample Conversation
![yt-summarizer-chat](https://github.com/finnless/yt-summarizer/assets/6785029/e9dfc9a0-34a3-4971-85a8-fafb91557791)

## Future Roadmap
- Image Recognition
