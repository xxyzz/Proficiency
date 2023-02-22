# Proficiency

Language files for [WordDumb](https://github.com/xxyzz/WordDumb).

## Data source

Wiktionary data come from kaikki.org and [Dbnary](https://kaiko.getalp.org/about-dbnary), Chinese Wiktionary data are created with the [Wiktextract](https://github.com/tatuylonen/wiktextract) tool. Word difficulty data sources are listed in each language subfolders.

## Dependencies

- Python

- wget: download files

- [lemminflect](https://github.com/bjascob/LemmInflect): inflect English words

- [Open Chinese Convert](https://github.com/BYVoid/OpenCC): convert Chinese characters

- [wordfreq](https://github.com/rspeer/wordfreq): get word frequency data

- [wiktextract-lemmatization](https://github.com/Vuizur/wiktextract-lemmatization): remove [stress](https://en.wikipedia.org/wiki/Stress_(linguistics))

- perl: Remove invalid unicode characters

- bunzip2

- [oxigraph](https://github.com/oxigraph/oxigraph)

## Create files

```
$ bash ./create_files.sh en
```

## License

This work is licensed under GPL version 3 or later.
