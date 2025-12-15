from fastapi import FastAPI
from pydantic import BaseModel
import re
import yake

app = FastAPI(title="YAKE Keywords API")


class Req(BaseModel):
    text: str
    max_keywords: int = 8


_CYR_RE = re.compile(r"[А-Яа-яЁё]")
_LAT_RE = re.compile(r"[A-Za-z]")


def detect_lang(text: str) -> str:
    cyr = len(_CYR_RE.findall(text))
    lat = len(_LAT_RE.findall(text))
    return "ru" if cyr >= max(20, lat) else "en"


def clean_text_for_yake(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    text = text.replace("{=tex}", " ")

    text = text.replace("`", "")

    text = text.replace("\\n", "\n")

    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(r"\bn(?=[А-Яа-яЁё])", "", text)

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_keywords(keywords: list[str], lang: str) -> list[str]:
    cleaned = []
    for kw in keywords:
        k = kw.strip()
        if not k:
            continue
        if k.lower() in {"tex"}:
            continue
        if len(k) < 3:
            continue
        cleaned.append(k)

    seen = set()
    out = []
    for k in cleaned:
        kl = k.lower()
        if kl not in seen:
            seen.add(kl)
            out.append(k)
    return out


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/keywords")
def keywords(req: Req):
    raw = (req.text or "").strip()
    if not raw:
        return {"language": "unknown", "keywords": [], "keywords_str": ""}

    text = clean_text_for_yake(raw)
    lang = detect_lang(text) if text else "unknown"

    if not text or lang == "unknown":
        return {"language": lang, "keywords": [], "keywords_str": ""}

    kw_extractor = yake.KeywordExtractor(
        lan=lang, n=1, top=req.max_keywords, dedupLim=0.9
    )

    pairs = kw_extractor.extract_keywords(text)
    kws = [k for k, _ in pairs]
    kws = clean_keywords(kws, lang)

    return {"language": lang, "keywords": kws, "keywords_str": ", ".join(kws)}
