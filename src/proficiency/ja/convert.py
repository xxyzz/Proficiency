def parse_jlpt_page(words: dict[str, int], level: int, title: str) -> None:
    from xml.etree import ElementTree

    import requests

    r = requests.get(
        "https://en.wiktionary.org/w/api.php",
        params={
            "format": "json",
            "formatversion": "2",
            "action": "parse",
            "page": title,
            "prop": "text",
        },
        headers={"user-agent": "proficiency"},
    )
    data = r.json()
    page_html = data.get("parse", {}).get("text", "")
    root = ElementTree.fromstring(page_html)
    for li_tag in root.iterfind(".//li"):
        for span_tag in li_tag.iterfind("span"):
            span_class = span_tag.get("class")
            if span_class in ["Jpan", "tr"]:  # "碌な" in "Appendix:JLPT/N1/ら行"
                span_text = "".join(span_tag.itertext()).strip()
                if span_text.startswith(
                    "（"
                ):  # "（カーペット）" in "Appendix:JLPT/N2/さ行"
                    span_text = span_text.strip("（） ")
                else:
                    for c in ["（", "("]:
                        # "二十（歳）" in "Appendix:JLPT/N3/は行"
                        # "あたたか(い)" in "Appendix:JLPT/N3/あ行"
                        if c in span_text:
                            span_text = span_text[: span_text.index(c)].strip()
                            break
                if len(span_text) > 0:
                    words[span_text] = level
        for a_tag in li_tag.iterfind("a"):  # N1, N2, N3 subpage
            parse_jlpt_page(words, level, a_tag.get("title", ""))


def main() -> None:
    """
    Convert the Wikitext of pages in https://en.wiktionary.org/wiki/Appendix:JLPT
    to difficulty value
    """
    import json

    words: dict[str, int] = {}
    for level in range(1, 6):
        parse_jlpt_page(words, level, f"Appendix:JLPT/N{level}")
    with open("difficulty.json", "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
