import mammoth
from pptx import Presentation


def docx_to_html(input_filename: str) -> str:
    with open(input_filename, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        return result.value


def pptx_to_txt(input_filename: str) -> str:
    presentation = Presentation(input_filename)
    presentation_text = ""

    for slide in presentation.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                presentation_text += f'\n{shape.text}'

    return presentation_text
