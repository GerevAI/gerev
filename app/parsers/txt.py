def txt_to_string(input_filename: str) -> str:
    with open(input_filename, 'r', encoding="utf-8") as file:
        return file.read()
