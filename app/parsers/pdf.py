from PyPDF2 import PdfReader
from typing import List
from langchain.document_loaders import PyPDFLoader
from langchain.schema import Document
from langchain.text_splitter import CharacterTextSplitter
def pdf_to_text(input_filename: str) -> str:
	pdf_file = PdfReader(input_filename)
	text=''
	
	for page in pdf_file.pages:
		text = text + page.extract_text()
	
	return text


def pdf_to_textV2(input_filename: str) -> str:
	loader = PyPDFLoader(input_filename)
	documents = loader.load()
	text_split = CharacterTextSplitter(chunk_size=256, chunk_overlap=0)
	texts = text_split.split_documents(documents)
	current_paragraph = ''
	for text in texts:
		paragraph = text.page_content
		if len(current_paragraph) > 0:
			current_paragraph += '\n\n'
		current_paragraph += paragraph.strip()

	return current_paragraph

