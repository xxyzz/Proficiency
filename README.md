# Proficiency

Language files for [WordDumb](https://github.com/xxyzz/WordDumb).

## Data source

Wiktionary data come from kaikki.org and [Dbnary](https://kaiko.getalp.org/about-dbnary), Chinese  and French Wiktionary data are created with the [Wiktextract](https://github.com/tatuylonen/wiktextract) tool. Word difficulty data sources are listed in each language subfolders.

## Dependencies

- Python

- wget: download files

- [lemminflect](https://github.com/bjascob/LemmInflect): inflect English words

- [Open Chinese Convert](https://github.com/BYVoid/OpenCC): convert Chinese characters

- [wordfreq](https://github.com/rspeer/wordfreq): get word frequency data

- [wiktextract-lemmatization](https://github.com/Vuizur/wiktextract-lemmatization): remove [stress](https://en.wikipedia.org/wiki/Stress_(linguistics))

- perl, sed: Remove invalid text

- lbunzip2 or bunzip2

- [oxigraph](https://github.com/oxigraph/oxigraph)

- pigz or gzip

## Create files
**Unix**:
```
$ python -m venv .venv
$ source .venv/bin/activate.fish
$ python -m pip install .
$ proficiency en
```

**Windows**:

First install wget with
```
winget install -e --id JernejSimoncic.Wget
```
and re-open the console window.

Then activate Python and run the program:
```
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install .
proficiency en
```

## License

This work is licensed under GPL version 3 or later.
