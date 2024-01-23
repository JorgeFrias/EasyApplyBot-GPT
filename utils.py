import re
from pathlib import Path
from itertools import takewhile

import math, time, config
from typing import List

class Markdown:
    @staticmethod
    def extract_content_from_markdown(markdown_text: str, title: str) -> str:
        """
        Extracts the content from a Markdown text, starting from a title.
        :param markdown_text: The Markdown text.
        :param title: The title to start from.
        :return: The content of the Markdown text, starting from the title, without the title.
        """
        content = ""
        found = False
        found_title_level = 0       # The level of the title we are looking for -> # Title -> level 1, ## Title -> level 2, etc.

        for line in markdown_text.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                line_title = re.sub(r'#\s*', '', line)
                current_title_level = len(list(takewhile(lambda c: c == '#', line)))

                if line_title == title:
                    found = True
                    found_title_level = current_title_level
                    continue
                elif found and current_title_level <= found_title_level:
                    break
            if found:
                content += line + '\n'

        return content.strip()

    @staticmethod
    def extract_content_from_markdown_file(file_path: Path, title: str) -> str:
        """
        Extracts the content from a Markdown file, starting from a title.
        :param file_path: The path to the Markdown file.
        :param title: The title to start from.
        :return: The content of the Markdown file, starting from the title, without the title.
        """
        with open(file_path, 'r') as file:
            markdown_text = file.read()

        return Markdown.extract_content_from_markdown(markdown_text, title)
