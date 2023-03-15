import re
from bs4 import BeautifulSoup

def html_to_text(html: str) -> str:
    # Becuase documents only contain text, we use a colon to separate subtitles from the text
    html = re.sub(r'(?=<\/h[1234567]>)', ': ', html)

    soup = BeautifulSoup(html, features='html.parser')
    plain_text = soup.get_text(separator="\n\n")

    # When there is a link immidiately followed by a symbol, BeautifulSoup adds whitespace between them. We remove it.
    plain_text = re.sub(r'\s+(?=[\.\?\!\:\,])', '', plain_text)
    return plain_text