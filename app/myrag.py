import os
import pandas as pd
import requests
import re
import sys
import shutil
import pickle
from langchain import hub
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from models import QueryResult

# Set the OCR_AGENT environment variable
os.environ["OCR_AGENT"] = "pytesseract"

IS_USING_IMAGE_RUNTIME = bool(os.getenv("IS_USING_IMAGE_RUNTIME", False))


def sanitize_string(input_string):
    # Remove special characters
    sanitized = re.sub(r"[^a-zA-Z0-9\s]", "", input_string.strip())
    # Convert to lowercase
    sanitized = sanitized.lower()
    # Replace spaces with hyphens
    sanitized = sanitized.replace(" ", "-")
    return sanitized


def download_pdfs_from_csv(csv_path, download_folder):
    # Read the CSV file
    df = pd.read_csv(csv_path)

    # Iterate over each row in the DataFrame
    name_2_path = {}
    for index, row in df.iterrows():
        restaurant_name = row["headline"]
        menu_url = row["menu_url"]

        # Generate a sanitized file name
        file_name = f"{sanitize_string(restaurant_name)}.pdf"
        file_path = os.path.join(download_folder, file_name)

        # Download the PDF
        try:
            response = requests.get(menu_url)
            response.raise_for_status()  # Check if the request was successful

            # Save the PDF to the specified folder
            with open(file_path, "wb") as file:
                file.write(response.content)
            print(f"Downloaded {file_name} successfully.")
            name_2_path[restaurant_name] = file_path
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {file_name}: {e}")

    df["file_path"] = df["headline"].map(name_2_path)
    df.to_csv("restaurant_menu_pdf.csv", index=False)


# Example usage
csv_path = "app/restaurant_menu_urls.csv"  # Path to your CSV file
download_folder = "menu_urls"  # Folder to save the downloaded PDFs


if not os.path.exists(download_folder) and not IS_USING_IMAGE_RUNTIME:
    os.makedirs(download_folder)
    print(f"Created folder: {download_folder}")

    # Download the PDFs
    download_pdfs_from_csv(csv_path, download_folder)

else:
    print(f"Folder already exists: {download_folder}")


embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
persist_directory = "./db"


def get_runtime_chroma_path():
    if IS_USING_IMAGE_RUNTIME:
        return f"/tmp/{persist_directory}"
    else:
        return persist_directory


def copy_chroma_to_tmp(CHROMA_PATH=persist_directory):
    dst_chroma_path = get_runtime_chroma_path()

    if not os.path.exists(dst_chroma_path):
        os.makedirs(dst_chroma_path)

    tmp_contents = os.listdir(dst_chroma_path)
    if len(tmp_contents) == 0:
        print(f"Copying ChromaDB from {CHROMA_PATH} to {dst_chroma_path}")
        os.makedirs(dst_chroma_path, exist_ok=True)
        shutil.copytree(CHROMA_PATH, dst_chroma_path, dirs_exist_ok=True)
    else:
        print(f"✅ ChromaDB already exists in {dst_chroma_path}")
    return dst_chroma_path


if os.path.exists(persist_directory) and os.listdir(persist_directory):

    # Hack needed for AWS Lambda's base Python image (to work with an updated version of SQLite).
    # In Lambda runtime, we need to copy ChromaDB to /tmp so it can have write permissions.
    if IS_USING_IMAGE_RUNTIME:
        __import__("pysqlite3")
        sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

        # move the file to /tmp and return the new path
        persist_directory = copy_chroma_to_tmp()

    print("Loading existing vectorstore...")
    vectorstore = Chroma(
        persist_directory=persist_directory, embedding_function=embeddings
    )
else:
    print("Creating new vectorstore...")
    # Load PDFs using langchain_community.document_loaders
    print("Loading data...")

    all_documents = []

    df = pd.read_csv("restaurant_menu_pdf.csv")

    for data in df.to_dict(orient="records"):
        fn = data["file_path"]
        if not fn or pd.isna(fn):
            continue

        cuisine = data["cuisine"]
        restaurant_name = data["headline"]
        location = data["location"]
        if restaurant_name.strip() == "Bar Goyana":
            print("skipping goyana")
        loader = PyMuPDFLoader(fn)
        print("Loading raw document..." + loader.file_path)
        raw_documents = loader.load()

        print("Splitting text...")
        text_splitter = RecursiveCharacterTextSplitter(
            separators=[
                "\n\n",
                "\n",
                " ",
                ".",
                ",",
                "\u200b",  # Zero-width space
                "\uff0c",  # Fullwidth comma
                "\u3001",  # Ideographic comma
                "\uff0e",  # Fullwidth full stop
                "\u3002",  # Ideographic full stop
                "",
            ],
            chunk_size=800,
            chunk_overlap=100,
            length_function=len,
        )
        documents = text_splitter.split_documents(raw_documents)

        #  add metadata
        for doc in documents:

            meta_dict = {
                "cuisine": cuisine.strip(),
                "restaurant_name": restaurant_name.strip(),
                "location": location.strip(),
            }
            doc.metadata = meta_dict

            doc.page_content += str(meta_dict) + "\n"

        all_documents.extend(documents)

    vectorstore = Chroma.from_documents(
        all_documents, embeddings, persist_directory=persist_directory
    )
    if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
        vectorstore.persist()


retriever = vectorstore.as_retriever()
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
prompt = hub.pull("rlm/rag-prompt")


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


from langchain_core.prompts import PromptTemplate

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

rag_chain_from_docs = (
    RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
    | custom_rag_prompt
    | llm
    | StrOutputParser()
)

rag_chain_with_source = RunnableParallel(
    {"context": retriever, "question": RunnablePassthrough()}
).assign(answer=rag_chain_from_docs)


# Function to ask questions
def ask_question(question):
    print("Answer:\n\n", end=" ", flush=True)
    ans = rag_chain_with_source.invoke(question)

    return ans


def query_rag(query_text):
    # Get the answer and fill in the QueryResult object
    answer = ask_question(query_text)

    return QueryResult(
        query_text=query_text,
        answer_text=answer.get("answer"),
        sources=[x.page_content for x in answer.get("context") if x.page_content],
        is_complete=True,
    )


# Example usage
if __name__ == "__main__":
    while True:
        user_question = input("Ask a question (or type 'quit' to exit): ")
        if user_question.lower() == "quit":
            break
        answer = ask_question(user_question)
        # print("\nFull answer received.\n")
