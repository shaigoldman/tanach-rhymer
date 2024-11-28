import json
from collections import defaultdict
from pathlib import Path
import re
import json
from hebrew import Hebrew


class HebrewC:
    text: Hebrew
    DAGESH = "ּ"

    def __init__(self, text: str | Hebrew):
        if isinstance(text, str):
            text = Hebrew(text)
        elif isinstance(text, HebrewC):
            text = text.text
        self.text = self.strip(text)

    @staticmethod
    def strip(text: Hebrew) -> Hebrew:
        clean_text = text.no_taamim().no_sof_passuk().__str__()
        to_remove = "[]()"
        return Hebrew(
            "".join(c for c in clean_text if c not in to_remove)
        )

    @staticmethod
    def remove_dagesh(text: str | Hebrew) -> str:
        if isinstance(text, Hebrew):
            text = text.__str__()
        clean_text = ""
        for letter in text:
            if letter == HebrewC.DAGESH:
                continue
            clean_text += letter

        return Hebrew(clean_text)

    def words(self):
        for word in re.split("־| ", self.text.__str__()):
            yield word

    def endswith(self, ending: str):
        clean_self = self.remove_dagesh(self.text)
        clean_ending = self.remove_dagesh(ending).__str__()
        return clean_self.endswith(clean_ending)

    def _bolded_word_iter(self, word: str):
        if not isinstance(word, str):
            word = word.__str__()
        for w in self.words():
            if w == word:
                yield f"**{w}**"
            else:
                yield w

    def bolded_word(self, word: str):
        return " ".join(self._bolded_word_iter(word))

    def stripped_str(self):
        return self.text.no_niqqud().__str__()

    def __str__(self):
        return self.text.__str__()

    def __repr__(self):
        return self.text.__repr__()

    def __eq__(self, other):
        if isinstance(other, HebrewC):
            return self.text == other.text
        return False

    def __hash__(self):
        return self.text.__hash__()


class Loc:
    book: str
    chap: int
    vers: int

    def __init__(self, book: str, chap: int, vers: int):
        self.book = book
        self.chap = chap
        self.vers = vers

    def __repr__(self):
        return f"<{self.book} {self.chap+1}:{self.vers+1}>"

    def dict(self):
        return {"book": self.book, "chap": self.chap, "vers": self.vers}

    @classmethod
    def from_str(cls, loc: str):
        book, loc = loc.split(" ")
        chap, vers = loc.split(":")
        return cls(book, int(chap) - 1, int(vers) - 1)


class Text:
    name: str
    _text: list[list[HebrewC]]

    def __init__(self, path: str):

        with Path(path).open("r") as f:
            data = json.load(f)

        self.name = self._get_name(data)
        self._text = self._get_text(data)
        self._clean_text()

    def __getitem__(self, loc: str | Loc) -> HebrewC:
        if isinstance(loc, str):
            loc = Loc.from_str(loc)
        if loc.book != self.name:
            raise ValueError(f"Book {loc.book} not in text")
        return self._text[loc.chap][loc.vers]

    def get_word(self, loc: str | Loc, word: str) -> HebrewC:
        return HebrewC(self[loc].bolded_word(word))

    def __iter__(self):
        for i, chap in enumerate(self._text):
            for j, vers in enumerate(chap):
                yield Loc(self.name, i, j), vers

    def iterwords(self):
        for loc, vers in self:
            for word in vers.words():
                yield loc, word

    def _clean_text(self):
        for i, chap in enumerate(self._text):
            for j, vers in enumerate(chap):
                self._text[i][j] = HebrewC(vers)

    @staticmethod
    def _get_name(data: dict) -> str:
        return data["available_versions"][0]["title"]

    @staticmethod
    def _get_text(data: dict) -> list[list[str]]:
        return data["versions"][0]["text"]


class TextCollection:
    name: str
    _texts: dict[str, Text]

    def __init__(self, name: str, base_path: str):
        self.name = name
        self._texts = {}
        for path in Path(base_path).iterdir():
            text = Text(path)
            self._texts[text.name] = text

    def __getitem__(self, name: str) -> Text:
        return self._texts[name]

    def __iter__(self):
        for text in self._texts.values():
            for loc, vers in text:
                yield loc, vers

    def iterwords(self):
        for loc, vers in self:
            for word in vers.words():
                yield loc, word


class Lexicon:
    def __init__(self, texts: TextCollection):
        self.texts = texts
        self._lex = self._make_lex()

    def __getitem__(self, word: str):
        query = HebrewC(word)
        return self._lex[query]

    def __iter__(self):
        for word in self._lex:
            yield word

    def _make_lex(self) -> defaultdict[HebrewC, set[tuple[int, int]]]:
        lex = defaultdict(set)
        for loc, word in self.texts.iterwords():
            lex[HebrewC(word)].add(loc)
        return lex


class Rhymer:
    def __init__(self, lex: Lexicon):
        self.lex = lex

    def rhymes(self, ending: str):
        for word in self.lex:
            if word.endswith(ending):
                yield word

    def ordered_rhymes(self, ending: str):
        return sorted(self.rhymes(ending), key=lambda x: x.stripped_str())

    def rhymes_locs(self, ending: str):
        rhymes = self.ordered_rhymes(ending)
        for rhyme in rhymes:
            yield rhyme, self.lex[rhyme]

    def rhymes_verses(self, ending: str):
        for rhyme, locs in self.rhymes_locs(ending):
            yield rhyme, [
                (loc, self.lex.texts[loc.book].get_word(loc, rhyme))
                for loc in set(locs)
            ]

    def rhymes_verses_json(self, ending: str):
        verses = []
        for rhyme, locs_verses in self.rhymes_verses(ending):
            verses.append(
                {
                    "word": rhyme.text.__str__(),
                    "verses": [
                        {"loc": loc.dict(), "vers": vers.__str__()}
                        for loc, vers in locs_verses
                    ],
                }
            )
        return json.dumps(verses)
