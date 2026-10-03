import re

POS_PATTERNS = [
    r"\bimprov(ed|es|ement)\b",
    r"\benhanc(e|es|ed|ement)\b",
    r"\bincreas(e|es|ed)\b",
    r"\bbenefit(s|ed)?\b",
    r"\bprotect(s|ed|ive)?\b",
    r"\bameliorat(e|es|ed)\b",
    r"\bpositive(ly)?\b",
    r"\bassociat(ed|es)? with (better|improved)\b",
    r"\brespons(e|ive)\b",
    r"\befficac(y|ious)\b",
]
NEG_PATTERNS = [
    r"\bworsen(s|ed)?\b",
    r"\bdecreas(e|es|ed)\b",
    r"\bnegative(ly)?\b",
    r"\bresistance\b",
    r"\btoxic(ity)?\b",
    r"\badverse\b",
    r"\bharm(ful)?\b",
]

POS_RE = re.compile("|".join(POS_PATTERNS), re.IGNORECASE)
NEG_RE = re.compile("|".join(NEG_PATTERNS), re.IGNORECASE)

def paper_sentiment_score(title, abstract):
    txt = f"{title}\n{abstract}"
    pos = len(POS_RE.findall(txt))
    neg = len(NEG_RE.findall(txt))
    return pos - neg  # >0 = more positive language
