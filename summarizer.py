# from langchain.document_loaders import YoutubeLoader
from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.llms import OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.summarize import load_summarize_chain
# from langchain.memory import ConversationBufferMemory

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

import re
import math

# Todo implement streaming
llm = OpenAI(temperature=0)

class Summarizer:
    def __init__(self, vectorstore=None):
        print('INIT CALLED')
        if vectorstore:
            self.vectorstore = vectorstore
        else:
            # Create vectorstore
            embeddings = OpenAIEmbeddings()
            self.vectorstore = Chroma("langchain_store", embeddings)

        # Create memory object / Conversation buffer
        # Note that having separate memory buffer from streamlit chat state could cause problems
        # LANGCHAIN BUG: ConversationBufferMemory can't handle sources
        # Set ConversationalRetrievalChain.from_llm( return_source_documents=True

        # Now passing in history manually
        # memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)


        # Create Chain
        # TODO enable return sources
        # TODO enable streaming
        self.qa = ConversationalRetrievalChain.from_llm(llm, self.vectorstore.as_retriever(), get_chat_history=self.get_chat_history, return_source_documents=True)

    # Custom get_chat_history for ConversationalRetrievalChain.from_llm
    @staticmethod
    def get_chat_history(messages) -> str:
        res = []
        for m in messages:
            if m['role'] == 'assistant':
                res.append(f"AI:{m['content']}")
            elif m['role'] == 'user':
                res.append(f"Human:{m['content']}")
            else:
                raise Exception('Chat history role must be assistant or user.')
            #res.append(f"Human:{human}\nAI:{ai}")
        return "\n".join(res)

    @staticmethod
    def extract_youtube_ids(s):
        youtube_regex = (
            r'(https?://)?(www\.)?'
            '(youtube\.com/watch\?v=|youtu\.be/)'
            '([^&=%\?]{11})'
        )

        ids = [match[3] for match in re.findall(youtube_regex, s)]
        return ids

    def retrieve_video(self, video_id):
        """
        Retrieves video transcript and metadata from YouTube.
        Returns Video Object or dict
        """
        # TODO Metadata - Change video loader to a custom loader class that inherits from langchain's YoutubeLoader
        # https://github.com/hwchase17/langchain/blob/560c4dfc98287da1bc0cfc1caebbe86d1e66a94d/langchain/document_loaders/youtube.py#L142-L250
        # YoutubeLoader creates a document from transcript instead of transcript_pieces which is what I want 
        # Or I could just call def _get_video_info(self) where self only needs a self.video_id
        # Old method. Now extracted in query.
        # video_id = YoutubeLoader.extract_video_id(url)
        # TODO fix bug missed "en-US"
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        video = {
            'transcript': transcript,
            'video_id': video_id
        }
        return video

    def chunkify_transcript(self, video, chunk_size=30, overlap=4):
        input_transcript = video['transcript']
        new_transcript = []
        index = 0
        while index < len(input_transcript):
            text = ' '.join([input_transcript[i]['text'] for i in range(index, min(index + chunk_size, len(input_transcript)))])
            start = input_transcript[index]['start']
            # Add section text, start time, and video id
            new_transcript.append({'text': text, 'start': start, 'video_id': video['video_id']})
            index += chunk_size - overlap
        return new_transcript

    def append_vectorstore(self, transcript):
        texts = [t['text'] for t in transcript]
        starts = [t['start'] for t in transcript]
        video_ids = [t['video_id'] for t in transcript]
        metadatas = [{'start': math.floor(t['start']), 'video_id': t['video_id']} for t in transcript]
        self.vectorstore.add_texts(texts, metadatas=metadatas)
        return

    def add_video(self, video_id):
        print(f'Adding video: {video_id}')
        video = self.retrieve_video(video_id)
        transcript = self.chunkify_transcript(video)
        self.append_vectorstore(transcript)
        return self.summarize_video(transcript)

    def summarize_video(self, transcript_pieces):
        # TODO Add video metadata to summary source
        docs = [Document(page_content=t["text"].strip(" ")) for t in transcript_pieces]
        chain = load_summarize_chain(llm, chain_type="map_reduce")
        summary = chain.run(docs)
        video_id = transcript_pieces[0]['video_id']
        metadatas = [{'start': 'TEST', 'video_id': video_id}]
        # Add summary to vectorstore
        self.vectorstore.add_texts([summary], metadatas=metadatas)
        return summary

    def new_query(self, messages):
        if messages[-1]['role'] == 'user':
            query = messages[-1]['content']
            chat_history = messages[:-1]
            # Check if query has youtube urls
            if (video_ids := self.extract_youtube_ids(query)) != []:
                print(f'Video ids found: {video_ids}. Adding only the first one.')
                try:
                    result = {'answer': f'I just watched that video. Here is a summary:\n\n{self.add_video(video_ids[0])}'}
                except (NoTranscriptFound, TranscriptsDisabled):
                    result = {'answer': f'I cannot find a transcript for {video_ids[0]}. Try another video.'}
            else:
                result = self.qa({"question": query, "chat_history": chat_history})
        else:
            raise Exception('Last message must have role user.')
        return result

