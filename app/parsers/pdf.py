from PyPDF2 import PdfReader

def pdf_to_text(input_filename: str) -> str:
	pdf_file = PdfReader(input_filename)
	text=''
	
	for page in pdf_file.pages:
		text = text + page.extract_text()
	
	return text