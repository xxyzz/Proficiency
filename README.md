# Proficiency

Language files for [WordDumb](https://github.com/xxyzz/WordDumb).

## Data source

English Wiktionary extracted data come from kaikki.org, Chinese Wiktionary data are created with the [Wiktextract](https://github.com/tatuylonen/wiktextract) tool. Word difficulty data sources are listed in each language subfolders.

## Dependencies

- wget: download files

- [lemminflect](https://github.com/bjascob/LemmInflect): inflect English words

- [Open Chinese Convert](https://github.com/BYVoid/OpenCC): convert Chinese characters

- [wordfreq](https://github.com/rspeer/wordfreq): get word frequency data

- [wiktextract-lemmatization](https://github.com/Vuizur/wiktextract-lemmatization): remove [stress](https://en.wikipedia.org/wiki/Stress_(linguistics))

## Create files

```
$ bash ./create_files.sh en
```

## License

This work is licensed under GPL version 3 or later.
