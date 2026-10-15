import os

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()


def get_index():
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    return pc.Index(os.environ.get("PINECONE_INDEX", "docuchat"))