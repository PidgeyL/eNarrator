import bs4
import ctypes
import gtts
import math
import pyaudio
import pydub
import pydub.playback
import pyttsx3
import queue
import sys
import tempfile
import threading
import yael

sys.settrace

class Book:
    def __init__(self, path=None):
        self.book    = None
        self.toc     = None
        if path:
            self.open(path)

    def open(self, path):
        self.book = yael.Publication(path)
        self._generate_toc()

    def _generate_toc(self):
        toc_dict = {}
        def crawl_toc(toc, d):
            if isinstance(toc, list):
                return [crawl_toc(x, "%s.%s"%(d, i+1)) for i,x in enumerate(toc)]
            elif isinstance(toc, yael.ncxtocnode.NCXTocNode):
                if len(d) == 2:
                    index = ".0"
                else:
                    index = d[2:]
                toc_dict[index[1:]] = toc
                crawl_toc(toc.children, d)
          
        crawl_toc(self.book.container.default_rendition.toc.children, "")
        self.toc = toc_dict

    def _get_text(self, chapter):
        ref = self.toc.get(chapter)
        if not ref:
            return None
        data = self.book.container.default_rendition.pac_document.manifest.item_by_id(ref.v_id)
        if data:
            text = ""
            soup = bs4.BeautifulSoup(data.contents, 'lxml')
            for hit in soup.findAll(['h1', 'h2', 'h3', 'h4', 'h5', 'p']):
                text += hit.text
                if hit.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
                    text += "\n\n"
            return text
        return None


class Narrator:
    def __init__(self):
        self.running  = False
        self.queue    = queue.Queue()
        self.narrator = None
        self.force_kill = False


    def _do_tts(self, text):
        if not text:
            return None
        try:
            tts = gtts.gTTS(text=text, lang='en')
            f = tempfile.TemporaryFile()
            tts.write_to_fp(f)
            f.seek(0)
            return pydub.AudioSegment.from_file(f)
        except Exception as e:
            print(e)
            return text


    def read(self, text, read_out=True):
        self.running = True
        if read_out:
            self.narrator = threading.Thread(target=self.narrate)
            self.narrator.start()
        chunks = []
        # Do magic of chopping up into incremental parts
        chunks = [text]
        for chunk in chunks:
            self.queue.put(self._do_tts(chunk))
        self.queue.put(None) # Signal to the player that this is the last part
        self.running = False


    def narrate(self):
        engine = pyttsx3.init()
        engine.setProperty('rate', 140)
        while (self.running or self.queue.qsize() != 0) and not self.force_kill:
            f = self.queue.get()
            if isinstance(f, str):
                engine.say(f)
                engine.runAndWait()
            elif isinstance(f, pydub.audio_segment.AudioSegment):
                #pydub.playback.play(f)
                self._play_audio(f)
            else:
                pass


    def stop_narrating(self):
        self.queue.queue.clear()
        self.running = False
        if self.narrator:
            self.force_kill = True


    def _play_audio(self, audio):
        ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None,         ctypes.c_char_p,
                                              ctypes.c_int, ctypes.c_char_p,
                                              ctypes.c_int, ctypes.c_char_p)
        def py_error_handler(filename, line, function, err, fmt):
            pass # suppress ALSA errors
        asound = ctypes.cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(ERROR_HANDLER_FUNC(py_error_handler))
        # Play the actual audio
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(audio.sample_width),
                        channels  =audio.channels,
                        rate      =audio.frame_rate,
                        output    =True)

        # This allows CTRL+C
        noc = math.ceil(len(audio) / float(500))
        chunks =  [audio[i * 500:(i + 1) * 500] for i in range(int(noc))]
        for chunk in chunks:
            if not self.force_kill:
                stream.write(chunk._data)
        stream.stop_stream()
        stream.close()
        p.terminate()
        self.force_kill = False
