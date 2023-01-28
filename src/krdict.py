import json
import scrapy

from scrapy.crawler import CrawlerProcess
from scrapy.http.response.html import HtmlResponse
from scrapy.selector.unified import Selector

DICTIONARY_PATH = "dictionaries"
LANGUAGE = "KOREAN"

SAVE_PATH = f"{DICTIONARY_PATH}/krdict_korean_{LANGUAGE.lower()}.json"

PAGE_ENTRIES = 100

if LANGUAGE == "ENGLISH":
    LANG_CODE = "eng"
    LANG_PARAMETERS = "nation=eng&nationCode=6"
elif LANGUAGE == "JAPANESE":
    LANG_CODE = "jpn"
    LANG_PARAMETERS = "nation=jpn&nationCode=7"
elif LANGUAGE == "KOREAN":
    LANG_CODE = ""
    LANG_PARAMETERS = ""

BASE_URL = f"https://krdict.korean.go.kr/{LANG_CODE}/dicSearchDetail/searchDetailWordsResult?"
BASE_PARAMETERS = f"{LANG_PARAMETERS}&searchFlag=Y&sort=W&ParaWordNo=&syllablePosition=&actCategoryList=&all_gubun=ALL&gubun=W&gubun=P&gubun=E&all_wordNativeCode=ALL&wordNativeCode=1&wordNativeCode=2&wordNativeCode=3&wordNativeCode=0&all_sp_code=ALL&sp_code=1&sp_code=2&sp_code=3&sp_code=4&sp_code=5&sp_code=6&sp_code=7&sp_code=8&sp_code=9&sp_code=10&sp_code=11&sp_code=12&sp_code=13&sp_code=14&sp_code=27&all_imcnt=ALL&imcnt=1&imcnt=2&imcnt=3&imcnt=0&all_multimedia=ALL&multimedia=P&multimedia=I&multimedia=V&multimedia=A&multimedia=S&multimedia=N&searchSyllableStart=&searchSyllableEnd=&searchOp=AND&searchTarget=word&searchOrglanguage=all&wordCondition=wordAll&myViewWord=27733&query=&blockCount={PAGE_ENTRIES}"

URL = lambda page : BASE_URL + BASE_PARAMETERS + f"&currentPage={page}"

BETWEEN_QUOTES = r"(?<=').*(?=')"
BETWEEN_BRACKETS = r"(?<=\().*(?=\))"
BETWEEN_SPECIAL_BRACKETS = r"(?<=「).*(?=」)"

dictionary = []

class KrdictSpider(scrapy.Spider):
    name = "naver"

    def start_requests(self):
        yield scrapy.Request(url=URL(1), callback=self.start_parse)
    
    def start_parse(self, response: HtmlResponse):
        page_count = int(response.css(".btn_last > a::attr(href)").re(BETWEEN_QUOTES)[0])

        self.parse_page(response)
        for page_num in range(2, page_count + 1):
            yield scrapy.Request(URL(page_num), callback=self.parse_page)

    def parse_page(self, response: HtmlResponse):
        global dictionary
        dictionary += [self.parse_term(entry) for entry in response.css(".search_result > dl")]

    def parse_term(self, selection: Selector):
        word = selection.css("dt > a > span::text").get().strip()
        stars = len(selection.css(".star > i"))

        homonym = selection.css("dt > a > span > sup::text").get()
        homonym = homonym.strip() if homonym != None else ""

        hanja_or_grammar = selection.css("dt > span:nth-child(2)::text")
        grammar_or_audio = selection.css("dt > span:nth-child(3)::text")

        hanja = hanja_or_grammar.re(BETWEEN_BRACKETS)
        hanja = hanja[0].strip() if len(hanja) != 0 else ""

        grammar_type = grammar_or_audio if hanja != "" else hanja_or_grammar
        grammar_type = grammar_type.re(BETWEEN_SPECIAL_BRACKETS)
        grammar_type = grammar_type[0].strip() if len(grammar_type) != 0 else ""

        audio_url = selection.css(".sound::attr(href)").re(BETWEEN_QUOTES)
        audio_url = audio_url[0] if len(audio_url) != 0 else ""

        entries = [entry.strip() for entry in selection.css("dd *::text").getall()]

        return {
            "word": word,
            "hanja": hanja,
            "stars": stars,
            "homonym": homonym,
            "grammar_type": grammar_type,
            "audio_url": audio_url,
            "entries": entries
        }

process = CrawlerProcess()
process.crawl(KrdictSpider)
process.start() # blocking

with open(SAVE_PATH, "w", encoding="utf-8") as file:
    json.dump(dictionary, file, ensure_ascii=False, indent=4)
