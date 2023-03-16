import mammoth


def docx_to_html(input_filename: str) -> str:
    with open(input_filename, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        return result.value
