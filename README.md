# Proficiency

Language files for [WordDumb](https://github.com/xxyzz/WordDumb).

## Data source

Wiktionary data come from https://kaikki.org

Word difficulty data sources are listed in each language subfolders.

## Dependencies

- Python

- [Wget](https://www.gnu.org/software/wget)

- [lemminflect](https://github.com/bjascob/LemmInflect): inflect English words

- [Open Chinese Convert](https://github.com/BYVoid/OpenCC): convert Chinese characters

- [wordfreq](https://github.com/rspeer/wordfreq): get word frequency data

- [wiktextract-lemmatization](https://github.com/Vuizur/wiktextract-lemmatization): remove [stress](https://en.wikipedia.org/wiki/Stress_(linguistics))

- [Perl](https://www.perl.org): Remove invalid text in Dbnary files

- lbzip2 or bzip2

- pigz or gzip

## Create files

```
$ python -m venv .venv
$ source .venv/bin/activate.fish
$ python -m pip install .
$ proficiency en
```

Change the [venv](https://docs.python.org/3/library/venv.html) invoke command according to your shell.

## License

This work is licensed under GPL version 3 or later.
