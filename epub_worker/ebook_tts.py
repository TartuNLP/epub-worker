import re
import io
import logging
import os
import json
import wave
import requests
from requests.auth import HTTPBasicAuth

from .config import EpubAPIConfig, TtsAPIConfig
from .schemas import Request #, Response

from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import zipfile
import numpy as np
from scipy.io import wavfile
from pydub import AudioSegment
from nltk import sent_tokenize

import warnings
warnings.filterwarnings("ignore", message="Warnings were encountered.")

logger = logging.getLogger(__name__)
GAP = re.compile(r'---( ---)*')
silence = np.zeros(10000, dtype=np.int16)
req = ['identifier', 'title', 'language', 'creator', 'contributor', 'publisher', 'rights', 'coverage', 'date', 'description']
epub_folder = '/opt/app/epub'
output_folder = '/opt/app/out'


class EBookTTS:
    def __init__(self, epub_api_config: EpubAPIConfig, tts_api_config: TtsAPIConfig):
        self.epub_api_config = epub_api_config
        self.epub_api_auth = HTTPBasicAuth(self.epub_api_config.username, self.epub_api_config.password)
        self.tts_api_config = tts_api_config
        self.tts_api_auth = HTTPBasicAuth(self.tts_api_config.username, self.tts_api_config.password)
        self.tts_request_counter = 0
    

    def is_cancelled(self):
        response = requests.get(f"{self.epub_api_config.protocol}://{self.epub_api_config.host}:{self.epub_api_config.port}/{self.current_job_id}/check",
                auth=self.epub_api_auth)
        if response.json():
            logger.info(f"Job {self.current_job_id} was cancelled.")
            return True
        return False

    
    def _synth_request(self, sent: str, filename: str):
        try:
            data_json = {
                "text": sent,
                "speaker": self.speaker,
                "speed": self.speed
            }
            with requests.post(f"{self.tts_api_config.protocol}://{self.tts_api_config.host}:{self.tts_api_config.port}/text-to-speech/v2",
                json=data_json,
                headers={'Content-Type': 'application/json'}, stream=True) as r:
                r.raise_for_status()
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return filename
        except Exception as e:
            return e


    def _synthesize_chapter(self, sentences, chapter_id):
        files = []
        counter = 0
        for sentence in sentences:
            self.tts_request_counter += 1
            if self.tts_request_counter % 1000 == 0:
                if self.is_cancelled():
                    logger.info("Stopping...")
                    return False
            counter += 1
            file_name = os.path.join(epub_folder, "sent-" + str(counter) + ".wav")
            if sentence:
                sent_file = self._synth_request(sentence, file_name)
                if type(sent_file) != str:
                    logger.info(f'Unsuccessful tts request - Chapter {chapter_id} sentence {counter}: {sentence}')
                    if str(sent_file).startswith("500") or str(sent_file).startswith("408"):
                        continue
                    return sent_file
                files.append(sent_file)
        waveforms = []
        for file in files:
            if waveforms:
                waveforms.append(silence)
            waveforms.append(wavfile.read(file)[1])
        waveforms = np.concatenate(waveforms)
        return waveforms
    

    def _recurse_toc(self, book):
        chapters = []
        for item in book.toc:
            if type(item) == ebooklib.epub.Link and BeautifulSoup(book.get_item_with_href(item.href).get_content(), features='xml').text.strip():
                chapters.append(item)
            elif type(item)==tuple and len(item)==2 and type(item[0])==ebooklib.epub.Section:
                chapters += self._recurse_toc(item[1])
        return chapters


    def _extract_content(self, book, chapters, toc_type=True):
        contents = []
        if toc_type:
            for i, chapter in enumerate(chapters):
                href = chapter.href.split('#')[0]

                content = book.get_item_with_href(href)
                content = BeautifulSoup(content.get_content(), features="lxml")
                text = re.sub('\s+', ' ', content.prettify()).strip()

                # Exact chapter start element is defined
                if "#" in chapter.href:
                    start = chapter.href.split('#')[1]
                    start = re.sub('\s+', ' ', content.find(id=start).prettify()).strip()
                    text = text[text.find(start):]

                # Next chapter starts inside the same content block
                if i+1 != len(chapters) and href == chapters[i+1].href.split('#')[0]:
                    stop = chapters[i+1].href.split('#')[1]
                    stop = re.sub('\s+', ' ', content.find(id=stop).prettify()).strip()
                    text = text[:text.find(stop)]

                content = BeautifulSoup(text)
                # remove text formatting
                for tag_type in ['i', 'u', 'b', 'em']:
                    for tag in content.find_all(tag_type):
                        tag.unwrap()
                content.smooth()
                contents.append(content)
        else:
            for chapter in chapters:
                content = BeautifulSoup(chapter.get_content(), features='xml')
                content = re.sub('\s+', ' ', content.prettify()).strip()
                content = BeautifulSoup(content, features='xml')
                content.smooth()
                contents.append(content)
        return contents
    
    def _parse_book(self, epub_file):
        '''Parse ebook file and convert chapters to a speech waveform.'''
        try:
            book = epub.read_epub(epub_file)
        except Exception as e:
            return str(e), f"{os.path.join(output_folder, os.path.splitext(epub_file)[0])}.zip"

        zip_name = f"{os.path.join(output_folder, book.title)}.zip"
        zip_file = zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED)

        f = open(os.path.join(output_folder, "metadata.txt"), 'w')
        for i in req:
            try:
                info = book.get_metadata('DC', i)
                if not info:
                    continue
                f.write(i + ': ' + str(info[0][0]) + '\n')
            except KeyError:
                continue
        
        chapters = self._recurse_toc(book)
        if chapters:
            contents = self._extract_content(book, chapters)
        else:
            chapters = [item for item in book.get_items() if ebooklib.ITEM_DOCUMENT == item.get_type()]
            contents = self._extract_content(book, chapters, False)
        
        f.write('chapters: ' + str([i.title for i in chapters]) + '\n')
        f.close()
        zip_file.write(os.path.join(output_folder, "metadata.txt"), arcname="metadata.txt")
        
        track = 0
        logger.info(f'{len(chapters)} chapters, {len(contents)} contents')
        for chapter, content in zip(chapters, contents):
            paragraphs = [paragraph.strip() for paragraph in content.stripped_strings]
            sentences = []
            for paragraph in paragraphs:
                for sentence in sent_tokenize(re.sub(r'[«»“„”]', r'"', paragraph), 'estonian'):
                    sentence = re.sub('\s+', ' ', sentence).strip()
                    sentences.append(sentence)
                sentences.append('')
            
            if sentences:
                track += 1
                
                filename = "{}_{:03d}".format(book.title, track)

                tags={"Title": chapter.title.strip(),
                    "File Name": filename,
                    "Track": track}

                with open(os.path.join(output_folder, f"{filename}_sents.txt"), 'w') as f:
                    f.write('\n'.join(sentences) + '\n')

                waveform = self._synthesize_chapter(sentences, track)
                if type(waveform) != np.ndarray:
                    zip_file.close()
                    return waveform, zip_name

                out = io.BytesIO()
                wavfile.write(out, 22050, waveform.astype(np.int16))

                chapter_audio = AudioSegment.from_wav(out)
                chapter_audio.export(os.path.join(output_folder, f"{filename}.mp3"),
                                    format = "mp3",
                                    codec = "mp3",
                                    tags=tags)
                zip_file.write(os.path.join(output_folder, f"{filename}.mp3"), arcname=f"{filename}.mp3")
        zip_file.close()

        return zip_name
    
    def respond_fail(self, error_message: str):
        logger.info("Job failed, posting error message to api.")
        requests.post(f"{self.epub_api_config.protocol}://{self.epub_api_config.host}:{self.epub_api_config.port}/{self.current_job_id}/failed",
                data={'error': error_message[:100]},
                auth=self.epub_api_auth)
    
    def respond(self, file_name: str):
        logger.info("Posting finished audiobook to api.")
        files = {
            'file': (file_name, open(file_name, 'rb'), 'application/zip'),
            'Content-Disposition': 'form-data; name="file"; filename="' + file_name + '"',
            'Content-Type': 'application/zip'
        }
        requests.post(f"{self.epub_api_config.protocol}://{self.epub_api_config.host}:{self.epub_api_config.port}/{self.current_job_id}/audiobook",
                files=files,
                auth=self.epub_api_auth)

    def predict_send(self, filename: str):
        output_file_name = self._parse_book(filename)
        if len(output_file_name) == 2:
            if output_file_name[0]:     #False only when job was manually cancelled
                self.respond_fail(str(output_file_name[0]))
            return output_file_name[1]
        self.respond(output_file_name)
        return output_file_name

    def _download_job_data(self, file_extension="epub"):
        filename = f"{os.path.join(epub_folder, self.current_job_id)}.{file_extension}"
        
        job_info = requests.get(f"{self.epub_api_config.protocol}://{self.epub_api_config.host}:{self.epub_api_config.port}/{self.current_job_id}", auth=self.epub_api_auth, stream=True).json()
        self.speaker = job_info['speaker']
        self.speed = job_info['speed']

        with requests.get(f"{self.epub_api_config.protocol}://{self.epub_api_config.host}:{self.epub_api_config.port}/{self.current_job_id}/epub", auth=self.epub_api_auth, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return filename
    
    def _clean_job(self, file_name: str, zip_file_name: str):
        for i in os.listdir(epub_folder):
            if i.startswith('sent-') and i.endswith('.wav'):
                os.remove(os.path.join(epub_folder, i))
        if os.path.exists(file_name):
            os.remove(file_name)
        if os.path.exists(zip_file_name):
            os.remove(zip_file_name)

    def process_request(self, request: Request):
        self.current_job_id = request.correlation_id
        filename = self._download_job_data(request.file_extension)
        zip_file_name = self.predict_send(filename)
        self._clean_job(filename, zip_file_name)