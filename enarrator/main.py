import argparse
import sys
import yael
import AdvancedInput

import eNarrator

class Color:
    GRAY     = '\033[90m';  END        = '\033[0m'
    RED      = '\033[91m';  BOLD       = '\033[1m'
    GREEN    = '\033[92m';  ITALIC     = '\033[3m'
    YELLOW   = '\033[93m';  UNDERLINE  = '\033[4m'
    BLUE     = '\033[94m';  INVERSE    = '\033[7m'
    PURPLE   = '\033[95m';  STRIKE     = '\033[9m'
    CYAN     = '\033[96m'
    WHITE    = '\033[97m'
    @classmethod
    def get_code(cls, text):
        return cls.__dict__.get(text.upper(), '')


def toc_list(toc):
    return [(k, v.v_text) for k, v in sorted(toc.items(), key=lambda x: int(x[1].v_play_order))]


def print_toc(toc, depth=1):
    margin = max([len(x[0]) for x in toc_list(toc)])
    for index, title in toc_list(toc):
        if len(index.split(".")) <= depth:
            print("\033[93m%s\033[0m - %s"%(index.ljust(margin), title))


def get_chapter(toc, chapter):
    chapter_list = []
    item = toc.get(chapter)
    if not item:
        return []
    chapter_list.append(chapter)
    for item in toc_list(toc):
        if item[0].startswith("%s."%chapter):
            chapter_list.append(item[0])
    return chapter_list


def interface(book=None):
    inp  = AdvancedInput.AdvancedInput()
    curs = "\033[92m\033[1m>> \033[0m"
    narrator = eNarrator.Narrator()

    if book:
        print_toc(book.toc, 1)
    while True:
        parts = inp.input(cursor=curs).split(' ', 1)
        command = parts[0].lower()
        data = parts[1].strip() if len(parts) == 2 else ""
        if command in ['toc'] and book:
            try:
                depth = int(data)
            except:
                depth = 1
            print_toc(book.toc, depth)
        elif command in ['read', 'play'] and book:
            chapters = []
            toc = toc_list(book.toc)
            # Generate playlist
            if data.lower() == "all":
                chapters = toc
            else:
                for chapter in [c.strip() for c in data.split(",")]:
                    if '-' in chapter:
                        start  = chapter.split('-')[0]
                        end    = chapter.split('-')[-1]
                        adding = False
                        for item in toc_list(book.toc):
                            if item[0] == start:
                                adding = True
                            if item[0] == end:
                                adding = False
                            if adding:
                                chapters.append(item[0])
                        chapters.extend(get_chapter(book.toc, end))
                    else:
                        chapter_list.extend(get_chapter(book.toc, chapter))
            # Generate text
            text=""
            for chapter in chapters:
                text+=book._get_text(chapter)
            narrator.read(text)
        elif command in ['stop']:
            narrator.stop_narrating()
        elif command in ['exit', 'quit']:
            sys.exit()
        


if __name__ == "__main__":
    argParser = argparse.ArgumentParser(description="Play epub books as audio files")
    argParser.add_argument('book', type=str, help='The book to read')
    args = argParser.parse_args()

    book = eNarrator.Book(args.book)
    interface(book)


