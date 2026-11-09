import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple


RUSSIAN_STOP_WORDS = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все", "она", "так", "его",
    "но", "да", "ты", "к", "у", "же", "вы", "за", "бы", "по", "только", "ее", "мне", "было", "вот", "от",
    "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда", "даже", "ну", "вдруг", "ли", "если", "уже",
    "или", "ни", "быть", "был", "него", "до", "вас", "нибудь", "опять", "уж", "вам", "ведь", "там", "потом",
    "себя", "ничего", "ей", "может", "они", "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их",
    "чем", "была", "сам", "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет", "ж", "тогда",
    "кто", "этот", "того", "потому", "этого", "какой", "совсем", "ним", "здесь", "этом", "один", "почти",
    "мой", "тем", "чтобы", "нее", "сейчас", "были", "куда", "зачем", "всех", "никогда", "можно", "при",
    "наконец", "два", "об", "другой", "хоть", "после", "над", "больше", "тот", "через", "эти", "нас", "про",
    "всего", "них", "какая", "много", "разве", "три", "эту", "моя", "впрочем", "хорошо", "свою", "этой",
    "перед", "иногда", "лучше", "чуть", "том", "нельзя", "такой", "им", "более", "всегда", "конечно", "всю", "между"
}

SPECIALTY_MAP = {
    "310819": "31.08.19 Педиатрия",
    "31.08.19": "31.08.19 Педиатрия",
    "педиатрия": "31.08.19 Педиатрия",
    "310835": "31.08.35 Инфекционные болезни",
    "31.08.35": "31.08.35 Инфекционные болезни",
    "инфекционные болезни": "31.08.35 Инфекционные болезни",
    "инфбол": "31.08.35 Инфекционные болезни",
    "310836": "31.08.36 Эпидемиология",
    "31.08.36": "31.08.36 Эпидемиология",
    "320812": "32.08.12 Эпидемиология",
    "32.08.12": "32.08.12 Эпидемиология",
    "эпидемиология": "32.08.12 Эпидемиология"
}

COMMON_ABBREVIATIONS = {
    "рпд": ["рабочая", "программа", "дисциплины", "рпд"],
    "рпп": ["рабочая", "программа", "практики", "рпп"],
    "фос": ["фонд", "оценочных", "средств", "фос", "тесты", "билеты", "задачи"],
    "руп": ["рабочий", "учебный", "план", "руп"],
    "гиа": ["государственная", "итоговая", "аттестация", "гиа"],
    "гэк": ["государственная", "экзаменационная", "комиссия", "гэк"],
    "умс": ["учебно", "методический", "совет", "умс"],
    "умк": ["учебно", "методическая", "комиссия", "умк"],
    "пк": ["приемная", "комиссия", "пк"],
    "ооп": ["основная", "образовательная", "программа", "ооп"]
}


def normalize_russian_token(token: str) -> str:
    token = token.lower().replace("ё", "е")
    token = re.sub(r"[^a-zа-я0-9]", "", token)
    if len(token) > 4 and token not in COMMON_ABBREVIATIONS:
        for suffix in (
            "ость", "ение", "ание", "ями", "ами", "ого", "его", "ому", "ему",
            "ыми", "ых", "их", "ую", "юю", "ие", "ые", "ое", "ее", "ов", "ев",
            "ей", "ам", "ям", "ах", "ях", "ом", "ем", "ой", "ей", "ый", "ий", "ию", "ии",
            "ия", "а", "я", "о", "е", "ы", "и", "у", "ю"
        ):
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                token = token[:-len(suffix)]
                break
    return token


def tokenize_text(text: str) -> List[str]:
    raw_tokens = re.findall(r"[a-zA-Zа-яА-Я0-9_.]+", text.lower().replace("ё", "е"))
    tokens = []
    for raw in raw_tokens:
        clean = re.sub(r"^[^a-zа-я0-9]+|[^a-zа-я0-9]+$", "", raw)
        if not clean or clean in RUSSIAN_STOP_WORDS:
            continue
        norm = normalize_russian_token(clean)
        if norm:
            tokens.append(norm)
            if norm in COMMON_ABBREVIATIONS:
                tokens.extend([normalize_russian_token(x) for x in COMMON_ABBREVIATIONS[norm]])
    return tokens


class NormativeDocument:
    __slots__ = (
        "doc_id", "file_name", "relative_path", "extension",
        "size_bytes", "category", "discipline", "code", "specialty", "search_text"
    )

    def __init__(
        self,
        doc_id: int,
        file_name: str,
        relative_path: str,
        extension: str,
        size_bytes: int,
        category: str,
        discipline: str,
        code: Optional[str],
        specialty: Optional[str],
        search_text: str
    ):
        self.doc_id = doc_id
        self.file_name = file_name
        self.relative_path = relative_path
        self.extension = extension
        self.size_bytes = size_bytes
        self.category = category
        self.discipline = discipline
        self.code = code
        self.specialty = specialty
        self.search_text = search_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.doc_id,
            "file_name": self.file_name,
            "relative_path": self.relative_path,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "category": self.category,
            "discipline": self.discipline,
            "code": self.code,
            "specialty": self.specialty
        }


class NormativeInvertedIndex:
    """
    Fast in-memory inverted index and filter engine for normative knowledge base catalog.
    Indexes 1,697 documents with sub-10ms query and snippet extraction.
    """
    def __init__(self, catalog_path: Optional[str] = None):
        self.documents: List[NormativeDocument] = []
        self.index: Dict[str, List[int]] = {}
        self.category_index: Dict[str, List[int]] = {}
        self.code_index: Dict[str, List[int]] = {}
        self.total_docs: int = 0
        self.catalog_path = catalog_path or self._resolve_catalog_path()
        if self.catalog_path and os.path.exists(self.catalog_path):
            self.load_catalog(self.catalog_path)

    @staticmethod
    def _resolve_catalog_path() -> str:
        cur = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(cur, "data", "normative", "corpus_catalog.json")
        if os.path.exists(candidate):
            return candidate
        cwd_candidate = os.path.join(os.getcwd(), "data", "normative", "corpus_catalog.json")
        return cwd_candidate

    @staticmethod
    def extract_metadata(file_name: str, relative_path: str, category: str) -> Tuple[str, Optional[str], Optional[str]]:
        full_str = f"{file_name} {relative_path} {category}"
        code_match = re.search(r"\b(\d{2}\.?\d{2}\.?\d{2})\b", full_str)
        code = None
        specialty = None
        if code_match:
            raw_code = code_match.group(1)
            dots_code = raw_code if "." in raw_code else f"{raw_code[:2]}.{raw_code[2:4]}.{raw_code[4:6]}"
            code = dots_code
            if dots_code in SPECIALTY_MAP:
                specialty = SPECIALTY_MAP[dots_code]
            elif raw_code in SPECIALTY_MAP:
                specialty = SPECIALTY_MAP[raw_code]

        if not specialty:
            lower_full = full_str.lower()
            if "педиатр" in lower_full:
                specialty = "31.08.19 Педиатрия"
                if not code:
                    code = "31.08.19"
            elif "инфекционн" in lower_full or "инфбол" in lower_full or "инф. бол" in lower_full:
                specialty = "31.08.35 Инфекционные болезни"
                if not code:
                    code = "31.08.35"
            elif "эпидемиолог" in lower_full:
                specialty = "32.08.12 Эпидемиология"
                if not code:
                    code = "32.08.12"

        base_name = os.path.splitext(file_name)[0]
        discipline = base_name
        prefixes = [
            "Аннотация к РПД ", "Аннотация к РПП ", "Рецензия на РПД ", "Рецензия на РПП ",
            "Рабочая программа ", "РПД 1 ", "РПД 2 ", "РПД 4 ", "РПД 5 ", "РПД 6 ", "РПД 7 ",
            "РПД 8  ", "РПД 9 ", "РПД ", "РПП  ", "РПП ", "ОХОП Образовательная программа ",
            "ООП ", "БИЛЕТЫ ГИА ", "ЗАДАЧИ ГИА ", "ГИА Тесты ", "Ключ ", "2026 Программа ВЭ 2026 ",
            "2025 РУП "
        ]
        for p in prefixes:
            if discipline.lower().startswith(p.lower()):
                discipline = discipline[len(p):].strip()
                break

        return discipline, code, specialty

    def load_catalog(self, catalog_path: str) -> int:
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.documents.clear()
        self.index.clear()
        self.category_index.clear()
        self.code_index.clear()

        doc_id = 0
        categories = data.get("categories", [])
        for cat_obj in categories:
            cat_name = cat_obj.get("category", "")
            for file_item in cat_obj.get("files", []):
                file_name = file_item.get("file_name", "")
                relative_path = file_item.get("relative_path", "")
                extension = file_item.get("extension", "")
                size_bytes = file_item.get("size_bytes", 0)
                file_cat = file_item.get("category", cat_name)

                discipline, code, specialty = self.extract_metadata(file_name, relative_path, file_cat)
                search_text = f"{file_name} {relative_path} {file_cat} {discipline} {code or ''} {specialty or ''}"

                doc = NormativeDocument(
                    doc_id=doc_id,
                    file_name=file_name,
                    relative_path=relative_path,
                    extension=extension,
                    size_bytes=size_bytes,
                    category=file_cat,
                    discipline=discipline,
                    code=code,
                    specialty=specialty,
                    search_text=search_text
                )
                self.documents.append(doc)

                if file_cat not in self.category_index:
                    self.category_index[file_cat] = []
                self.category_index[file_cat].append(doc_id)

                if code:
                    clean_code = code.replace(".", "")
                    for c in (code, clean_code):
                        if c not in self.code_index:
                            self.code_index[c] = []
                        self.code_index[c].append(doc_id)

                tokens = tokenize_text(search_text)
                seen_tokens: Set[str] = set()
                for token in tokens:
                    if token not in seen_tokens:
                        seen_tokens.add(token)
                        if token not in self.index:
                            self.index[token] = []
                        self.index[token].append(doc_id)

                doc_id += 1

        self.total_docs = len(self.documents)
        return self.total_docs

    def get_doc(self, doc_id: int) -> Optional[NormativeDocument]:
        if 0 <= doc_id < len(self.documents) and self.documents[doc_id].doc_id == doc_id:
            return self.documents[doc_id]
        for d in self.documents:
            if d.doc_id == doc_id:
                return d
        return None

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        code: Optional[str] = None,
        specialty: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        matched_doc_ids: Optional[Set[int]] = None

        clean_query = query.strip()
        query_tokens = tokenize_text(clean_query) if clean_query else []

        if query_tokens:
            for token in query_tokens:
                token_matches = set(self.index.get(token, []))
                if not token_matches:
                    for indexed_token, ids in self.index.items():
                        if token in indexed_token or indexed_token in token:
                            token_matches.update(ids)
                if matched_doc_ids is None:
                    matched_doc_ids = token_matches
                else:
                    matched_doc_ids = matched_doc_ids.intersection(token_matches)
                if not matched_doc_ids:
                    break
        else:
            matched_doc_ids = set(range(self.total_docs))

        if matched_doc_ids is None:
            matched_doc_ids = set()

        if category:
            cat_ids = set(self.category_index.get(category, []))
            if not cat_ids:
                cat_ids = {doc.doc_id for doc in self.documents if category.lower() in doc.category.lower()}
            matched_doc_ids = matched_doc_ids.intersection(cat_ids)

        if code:
            norm_code = code.strip().replace(".", "")
            code_ids = set(self.code_index.get(code, [])) | set(self.code_index.get(norm_code, []))
            if not code_ids:
                code_ids = {doc.doc_id for doc in self.documents if doc.code and (norm_code in doc.code.replace(".", ""))}
            matched_doc_ids = matched_doc_ids.intersection(code_ids)

        if specialty:
            spec_lower = specialty.strip().lower()
            matched_doc_ids = {
                doc_id for doc_id in matched_doc_ids
                if self.get_doc(doc_id) and self.get_doc(doc_id).specialty and spec_lower in self.get_doc(doc_id).specialty.lower()
            }

        scored_results: List[Tuple[float, NormativeDocument, str]] = []
        for doc_id in matched_doc_ids:
            doc = self.get_doc(doc_id)
            if not doc:
                continue
            score = 0.0
            name_lower = doc.file_name.lower()
            disc_lower = doc.discipline.lower()

            if clean_query:
                clean_q_lower = clean_query.lower()
                if clean_q_lower in name_lower:
                    score += 50.0
                if clean_q_lower in disc_lower:
                    score += 40.0
                for t in query_tokens:
                    if t in name_lower:
                        score += 15.0
                    if t in disc_lower:
                        score += 10.0
                    if t in doc.category.lower():
                        score += 5.0

            snippet = self._generate_snippet(doc, query_tokens)
            scored_results.append((score, doc, snippet))

        scored_results.sort(key=lambda x: (x[0], -len(x[1].file_name)), reverse=True)
        top_results = scored_results[:limit]

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "query": query,
            "total_hits": len(scored_results),
            "elapsed_ms": round(elapsed_ms, 3),
            "results": [
                {
                    **doc.to_dict(),
                    "relevance_score": round(score, 2),
                    "snippet": snippet
                }
                for score, doc, snippet in top_results
            ]
        }

    def _generate_snippet(self, doc: NormativeDocument, query_tokens: List[str]) -> str:
        full_text = f"{doc.file_name} | {doc.relative_path} | {doc.category}"
        if not query_tokens:
            return full_text[:120] + ("..." if len(full_text) > 120 else "")
        for token in query_tokens:
            match = re.search(re.escape(token), full_text, flags=re.IGNORECASE)
            if match:
                start = max(0, match.start() - 30)
                end = min(len(full_text), match.end() + 50)
                snippet = full_text[start:end].strip()
                if start > 0:
                    snippet = "..." + snippet
                if end < len(full_text):
                    snippet = snippet + "..."
                return snippet
        return full_text[:120] + ("..." if len(full_text) > 120 else "")

    def get_categories(self) -> List[Dict[str, Any]]:
        return [
            {"category": cat, "count": len(ids)}
            for cat, ids in sorted(self.category_index.items(), key=lambda x: len(x[1]), reverse=True)
        ]

    def get_specialties(self) -> List[str]:
        specs = {doc.specialty for doc in self.documents if doc.specialty}
        return sorted(list(specs))


_GLOBAL_INDEX: Optional[NormativeInvertedIndex] = None


def get_normative_index(catalog_path: Optional[str] = None) -> NormativeInvertedIndex:
    global _GLOBAL_INDEX
    if _GLOBAL_INDEX is None:
        _GLOBAL_INDEX = NormativeInvertedIndex(catalog_path=catalog_path)
    return _GLOBAL_INDEX
