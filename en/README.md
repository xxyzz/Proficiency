# English

## Data source

- [kaikki.org](https://kaikki.org/dictionary/English/index.html)

- [*Estimating the prevalence and diversity of words in written language*](https://btjohns.com/pubs/JDJ_QJEP_2020.pdf): [Excel file](https://btjohns.com/JDJ_Prev_supp.xlsx)

- Some Word Wise enabled books

## Convert difficulty level

Convert the semantic diversity-author prevalence(SD-AP) value:

- SD-AP >= 4: 5

- SD-AP >= 3: 4

- SD-AP >= 2: 3

- SD-AP >= 1: 2

- SD-AP < 1: 1

## Data format

`kindle_all_lemmas.csv`:


```
lemma,pos,sense_id,display_lemma_id
'neath,preposition,69182,75849
```

`kindle_enabled_lemmas.json`:

```
{
  "'neath": [       // word
    1,             // difficulty
    69182,         // sense id
    "preposition"  // POS type
  ],
...
```

## Dependencies

- [lemminflect](https://github.com/bjascob/LemmInflect)

- [flashtext](https://github.com/vi3k6i5/flashtext)
