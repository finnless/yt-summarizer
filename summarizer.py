import re
import math
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.summarize import load_summarize_chain

from langchain.document_loaders import YoutubeLoader


class Summarizer:
    def __init__(self, openai_api_key=None, vectorstore=None):
        # Define the language model
        self.llm4 = ChatOpenAI(openai_api_key=openai_api_key, temperature=0, model='gpt-4')
        self.llm35 = ChatOpenAI(openai_api_key=openai_api_key, temperature=0, model='gpt-3.5-turbo')
        self.llm3 = OpenAI(openai_api_key=openai_api_key, temperature=0)
        self.vectorstore = vectorstore or self.init_vectorstore(openai_api_key)
        self.qa = ConversationalRetrievalChain.from_llm(self.llm4, self.vectorstore.as_retriever(), get_chat_history=self.get_chat_history, return_source_documents=True, condense_question_llm = self.llm35)

    def init_vectorstore(self, openai_api_key):
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        return Chroma("langchain_store", embeddings)

    @staticmethod
    def get_chat_history(messages) -> str:
        """
        Custom function for ConversationalRetrievalChain.from_llm.
        It converts chat history to a string format.
        """
        chat_hist = [f"{m['role'].capitalize()}:{m['content']}" for m in messages if m['role'] in ('assistant', 'user')]

        return "\n".join(chat_hist)

    @staticmethod
    def extract_youtube_ids(s):
        """
        Extracts youtube video ids from a string using regex.
        """
        youtube_regex = (
            r'(https?://)?(www\.)?'
            '(youtube\.com/watch\?v=|youtu\.be/)'
            '([^&=%\?]{11})'
        )
        return [match[3] for match in re.findall(youtube_regex, s)]

    @staticmethod
    def get_video_info(video_id):
        """
        Extracts video metadata from youtube video id.
        Hacky ugly wrapper for langchain's YoutubeLoader.
        """
        dummy = type("Dummy", (object,), {})()
        dummy.video_id = video_id
        meta = YoutubeLoader._get_video_info(dummy)
        return meta

    def retrieve_video(self, video_id):
        """
        Retrieves video transcript and metadata from YouTube.
        """
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return {'transcript': transcript, 'video_id': video_id}

    def chunkify_transcript(self, video, chunk_size=50, overlap=5):
        """
        Splits the video transcript into chunks.
        """
        input_transcript = video['transcript']
        transcript_len = len(input_transcript)
        splits = range(0, transcript_len, chunk_size - overlap)

        new_transcript = [
            {
                'text': ' '.join([input_transcript[i]['text'] for i in range(index, min(index + chunk_size, transcript_len))]),
                'start': input_transcript[index]['start'],
                'video_id': video['video_id']
            } for index in splits
        ]

        return new_transcript

    def append_vectorstore(self, transcript):
        """
        Adds transcript text to the vectorstore.
        """
        texts = [t['text'] for t in transcript]
        metadatas = [{'start': math.floor(t['start']), 'video_id': t['video_id']} for t in transcript]

        self.vectorstore.add_texts(texts, metadatas=metadatas)

    def add_video(self, video_id):
        """
        Adds a new video to the vectorstore.
        """
        video = self.retrieve_video(video_id)
        transcript = self.chunkify_transcript(video)

        self.append_vectorstore(transcript)

        return self.summarize_video(transcript)

    def summarize_video(self, transcript_pieces):
        """
        Summarizes a video transcript.
        """
        docs = [Document(page_content=t["text"].strip(" ")) for t in transcript_pieces]
        chain = load_summarize_chain(self.llm3, chain_type="map_reduce")
        summary = chain.run(docs)

        metadatas = [{'start': 'TEST', 'video_id': transcript_pieces[0]['video_id']}]

        self.vectorstore.add_texts([summary], metadatas=metadatas) # Add summary to vectorstore

        return summary

    def new_query(self, messages):
        """
        Handles a new query by either adding a new video or answering a question.
        """
        if messages[-1]['role'] != 'user':
            raise ValueError('Last message must be by the user.')

        query = messages[-1]['content']
        chat_history = messages[:-1]

        video_ids = self.extract_youtube_ids(query)

        if video_ids:
            try:
                result = {'answer': f'I just watched that video. Feel free to ask me questions about it. Here is a summary:\n\n{self.add_video(video_ids[0])}'}
            except (NoTranscriptFound, TranscriptsDisabled):
                result = {'answer': f'I cannot find a transcript for {video_ids[0]}. Try another video.'}
        else:
            result = self.qa({"question": query, "chat_history": chat_history})

        return result
