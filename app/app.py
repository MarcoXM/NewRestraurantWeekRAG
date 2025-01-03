# Install Streamlit if not already installed
# !pip install streamlit

import os
import pandas as pd
import requests
import re
import pickle
import streamlit as st
from langchain import hub
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# Set the OCR_AGENT environment variable
os.environ['OCR_AGENT'] = 'pytesseract'

# Function to sanitize strings
def sanitize_string(input_string):
    sanitized = re.sub(r'[^a-zA-Z0-9\s]', '', input_string.strip())
    sanitized = sanitized.lower()
    sanitized = sanitized.replace(' ', '-')
    return sanitized

# Function to download PDFs from CSV
def download_pdfs_from_csv(csv_path, download_folder):
    df = pd.read_csv(csv_path)
    name_2_path = {}
    for index, row in df.iterrows():
        restaurant_name = row['headline']
        menu_url = row['menu_url']
        file_name = f"{sanitize_string(restaurant_name)}.pdf"
        file_path = os.path.join(download_folder, file_name)
        try:
            response = requests.get(menu_url)
            response.raise_for_status()
            with open(file_path, 'wb') as file:
                file.write(response.content)
            name_2_path[restaurant_name] = file_path
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {file_name}: {e}")
    df['file_path'] = df['headline'].map(name_2_path)
    df.to_csv('restaurant_menu_pdf.csv', index=False)

# Ensure the download folder exists
csv_path = 'app/restaurant_menu_urls.csv'
download_folder = 'menu_urls'
if not os.path.exists(download_folder):
    os.makedirs(download_folder)
    download_pdfs_from_csv(csv_path, download_folder)

# Load embeddings and vectorstore
embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
persist_directory = "./db"
if os.path.exists(persist_directory) and os.listdir(persist_directory):
    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
else:
    all_documents = []
    df = pd.read_csv('restaurant_menu_pdf.csv')
    for data in df.to_dict(orient="records"):
        fn = data["file_path"]
        if not fn or pd.isna(fn):
            continue
        cuisine = data["cuisine"]
        restaurant_name = data["headline"]
        location = data["location"]
        if restaurant_name.strip() == "Bar Goyana":
            continue
        loader = PyMuPDFLoader(fn)
        raw_documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", " ", ".", ",", "\u200b", "\uff0c", "\u3001", "\uff0e", "\u3002", ""],
            chunk_size=800,
            chunk_overlap=100,
            length_function=len,
        )
        documents = text_splitter.split_documents(raw_documents)
        for doc in documents:
            meta_dict = {'cuisine': cuisine.strip(), 'restaurant_name': restaurant_name.strip(), 'location': location.strip()}
            doc.metadata = meta_dict
            doc.page_content += str(meta_dict) + "\n"
        all_documents.extend(documents)
    vectorstore = Chroma.from_documents(all_documents, embeddings, persist_directory=persist_directory)
    if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
        vectorstore.persist()

retriever = vectorstore.as_retriever()
llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
prompt = hub.pull("rlm/rag-prompt")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

template = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
when you answer the question,
Rule 1:
    Add 1st Section for Listing the restaurant name, location, and cuisine:
    it must include the restaurant_name, the location, and the cuisine from the metadata. the metadata is a dictionary that is attached to the document.
    and please Quote the metadata in the answer with **bold**.
Rule 2:
    Add 2nd Section for Listing the menu type and prices:
    the price for restrauant week, and the menu item name should be in the format of:
    each menu should be in a separate line.
    the price should be in the format of $xx.xx
Rule 3:
    if there are Lunch and Dinner menus, please answer for both. with the Lunch menu first.
    separate the answers for the Lunch and Dinner menus with a line break.
    if there is only one menu, just answer for that menu
Rule 4:
    Details for Listing dishes and ingredients:
    List all the selections for each choices of menu items and Catgorized by parts of the meal like Appetizers, Entrees, Desserts, or other parts etc. 
    Each dish and its ingredients should be in a separate line.
Rule 5:
    Add 3rd section for the best selections:
    List the best selections (choose the most high rated menu items.)
    if there are Lunch and Dinner menus, please answer for both. with the Lunch Best Selections first.
    separate the answers for the Lunch and Dinner Best Selections with a line break.
    if there is only one menu, just answer for that menu'Best Selections
    For the selected menu items, if possible explain why they are the best selections. The answer should be right after your selection.



Always say "thanks for asking!" at the end of the answer.
{context}
Question: {question}
Helpful Answer:"""
custom_rag_prompt = PromptTemplate.from_template(template)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | custom_rag_prompt
    | llm
    | StrOutputParser()
)

def ask_question(question):
    answer = ""
    for chunk in rag_chain.stream(question):
        answer += chunk
    return answer

# Streamlit app
st.title("New York Restaurant Week")
st.write("Ask questions about restaurant menus and get detailed answers.")

# Add a picture
st.image("img/nycrw.jpg", caption="New York Restaurant Week")

user_question = st.text_input("Ask a question:")
if user_question:
    answer = ask_question(user_question)
    st.write("Answer:")
    st.write(answer)