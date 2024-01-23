import re
from pathlib import Path
from itertools import takewhile

import math, time, config
from typing import List

from selenium import webdriver

def chromeBrowserOptions():
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-extensions")
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-port=9222')
    if(config.headless):
        options.add_argument("--headless")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    if(len(config.chromeProfilePath)>0):
        initialPath = config.chromeProfilePath[0:config.chromeProfilePath.rfind("/")]
        profileDir = config.chromeProfilePath[config.chromeProfilePath.rfind("/")+1:]
        options.add_argument('--user-data-dir=' +initialPath)
        options.add_argument("--profile-directory=" +profileDir)
    else:
        options.add_argument("--incognito")
    return options

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

def prYellow(prt):
    print(f"\033[93m{prt}\033[00m")
