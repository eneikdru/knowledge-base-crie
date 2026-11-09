import json
import math
import os
import re
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple


RUSSIAN_STOPWORDS: Set[str] = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все", "она",
    "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за", "бы", "по", "только", "ее",
    "мне", "было", "вот", "от", "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда",
    "даже", "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был", "него", "до",
    "вас", "нибудь", "опять", "уж", "вам", "ведь", "там", "потом", "себя", "ничего", "ей",
    "может", "они", "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем",
    "была", "сам", "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет",
    "ж", "тогда", "кто", "этот", "того", "потому", "этого", "какой", "совсем", "ним", "здесь"
}

RUSSIAN_ABBREVIATIONS: Dict[str, List[str]] = {
    "рпд": ["рпд", "рабочая", "программа", "дисциплины", "дисциплин"],
    "фос": ["фос", "фонд", "оценочных", "средств"],
    "руп": ["руп", "учебный", "план", "планы"],
    "гиа": ["гиа", "государственная", "итоговая", "аттестация"],
    "гэк": ["гэк", "государственная", "экзаменационная", "комиссия"],
    "умс": ["умс", "учебно", "методический", "совет"],
    "умк": ["умк", "учебно", "методическая", "комиссия"],
    "пк": ["пк", "приемная", "комиссия"],
    "ооп": ["ооп", "образовательная", "программа"],
    "вэ": ["вэ", "вступительные", "экзамены", "испытания"],
    "цнииэ": ["цнииэ", "эпидемиологии"],
    "ккг": ["ккг", "календарный", "учебный", "график"],
    "ппс": ["ппс", "профессорско", "преподавательский", "состав"]
}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9._/\\\-\s]", " ", text)
    return text


def stem_word(word: str) -> str:
    w = word.lower().replace("ё", "е")
    if len(w) <= 3:
        return w
    
    # Common Russian suffixes in administrative and educational documents
    suffixes = (
        "иями", "ями", "ами", "ости", "ость", "ение", "ения", "ению", "ением",
        "ация", "ации", "ацию", "ацией", "иями", "иями", "ного", "ному", "ным",
        "ных", "ная", "ное", "ной", "ную", "ные", "ских", "скому", "ский",
        "ская", "ское", "ской", "ские", "скую", "овах", "овый", "овая", "овое",
        "овой", "овые", "овых", "ями", "ами", "ях", "ах", "ей", "ой", "ий",
        "ый", "ая", "ое", "ые", "ым", "ом", "ам", "ем", "ев", "ов", "ия",
        "ья", "ию", "ью", "ие", "ье", "ей", "ся", "сь", "а", "е", "и", "о", "у", "ы", "ь"
    )
    for sfx in suffixes:
        if w.endswith(sfx) and len(w) - len(sfx) >= 3:
            return w[:-len(sfx)]
    return w


def tokenize(text: str) -> List[str]:
    norm = normalize_text(text)
    raw_tokens = re.findall(r"[a-zа-я0-9]+(?:\.[a-zа-я0-9]+)*", norm)
    tokens = []
    for t in raw_tokens:
        t_clean = t.strip(".")
        if not t_clean or t_clean in RUSSIAN_STOPWORDS:
            continue
        tokens.append(t_clean)
    return tokens


def extract_specialties(text: str) -> List[str]:
    specs = []
    # Matches patterns like 31.08.19, 31.08.35, 32.08.12, 310819, 310835, 320812
    matches_dotted = re.findall(r"\b(\d{2}\.\d{2}\.\d{2})\b", text)
    for m in matches_dotted:
        specs.append(m)
    matches_compact = re.findall(r"\b(3108\d{2}|3208\d{2})\b", text)
    for m in matches_compact:
        formatted = f"{m[:2]}.{m[2:4]}.{m[4:]}"
        if formatted not in specs:
            specs.append(formatted)
    return list(set(specs))


def detect_document_type(file_name: str, relative_path: str, category: str) -> str:
    combined = f"{file_name} {relative_path} {category}".lower()
    if "положен" in combined:
        return "Положения"
    if "регламент" in combined:
        return "Регламенты"
    if "поряд" in combined:
        return "Порядки"
    if "правил" in combined:
        return "Правила"
    if "инструкц" in combined:
        return "Инструкции"
    if "протокол" in combined:
        if "пк" in combined or "приемн" in combined:
            return "Протоколы ПК"
        if "гэк" in combined or "экзамен" in combined:
            return "Протоколы ГЭК"
        if "умс" in combined or "учебно метод" in combined or "умк" in combined:
            return "Протоколы УМС"
        return "Протоколы"
    if "фос" in combined or "билет" in combined or "задач" in combined or "тест" in combined:
        return "ФОС"
    if "рпд" in combined or "рабочая программа" in combined:
        return "РПД"
    if "руп" in combined or "учебный план" in combined:
        return "РУП"
    if "аттестац" in combined:
        return "Аттестации"
    return "Прочие"


class NormativeDocument:
    __slots__ = (
        "doc_id", "file_name", "relative_path", "extension",
        "size_bytes", "category", "doc_type", "specialties",
        "tokens", "stemmed_tokens"
    )

    def __init__(
        self,
        doc_id: int,
        file_name: str,
        relative_path: str,
        extension: str,
        size_bytes: int,
        category: str,
        doc_type: str,
        specialties: List[str],
        tokens: List[str],
        stemmed_tokens: List[str]
    ):
        self.doc_id = doc_id
        self.file_name = file_name
        self.relative_path = relative_path
        self.extension = extension
        self.size_bytes = size_bytes
        self.category = category
        self.doc_type = doc_type
        self.specialties = specialties
        self.tokens = tokens
        self.stemmed_tokens = stemmed_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "file_name": self.file_name,
            "relative_path": self.relative_path,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "category": self.category,
            "doc_type": self.doc_type,
            "specialties": self.specialties
        }


class InvertedIndex:
    def __init__(self):
        self.documents: List[NormativeDocument] = []
        # term -> list of (doc_id, weight)
        self.index: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        # filter indices
        self.by_category: Dict[str, Set[int]] = defaultdict(set)
        self.by_doc_type: Dict[str, Set[int]] = defaultdict(set)
        self.by_specialty: Dict[str, Set[int]] = defaultdict(set)
        self.total_docs: int = 0
        self.is_loaded: bool = False
        self.load_duration_ms: float = 0.0

    def load_from_catalog(self, catalog_path: str) -> int:
        start_time = time.perf_counter()
        if not os.path.isabs(catalog_path):
            catalog_path = os.path.abspath(catalog_path)

        if not os.path.exists(catalog_path):
            raise FileNotFoundError(f"Catalog file not found at: {catalog_path}")

        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.documents.clear()
        self.index.clear()
        self.by_category.clear()
        self.by_doc_type.clear()
        self.by_specialty.clear()

        categories = data.get("categories", [])
        doc_counter = 0

        for cat_info in categories:
            category_name = cat_info.get("category", "Общее")
            files = cat_info.get("files", [])
            for file_entry in files:
                fname = file_entry.get("file_name", "")
                rel_path = file_entry.get("relative_path", "")
                ext = file_entry.get("extension", "")
                size_bytes = file_entry.get("size_bytes", 0)
                assigned_category = file_entry.get("category", category_name)

                searchable_text = f"{fname} {rel_path} {assigned_category}"
                tokens = tokenize(searchable_text)
                stemmed = [stem_word(t) for t in tokens]
                specs = extract_specialties(searchable_text)
                dtype = detect_document_type(fname, rel_path, assigned_category)

                doc = NormativeDocument(
                    doc_id=doc_counter,
                    file_name=fname,
                    relative_path=rel_path,
                    extension=ext,
                    size_bytes=size_bytes,
                    category=assigned_category,
                    doc_type=dtype,
                    specialties=specs,
                    tokens=tokens,
                    stemmed_tokens=stemmed
                )
                self.documents.append(doc)

                # Index term frequencies
                tf: Dict[str, float] = defaultdict(float)
                for t in tokens:
                    tf[t] += 1.5
                for s in stemmed:
                    tf[s] += 1.0

                # Higher boost for exact terms in file_name
                for fn_token in tokenize(fname):
                    tf[fn_token] += 3.0
                    tf[stem_word(fn_token)] += 2.0

                for term, score in tf.items():
                    self.index[term].append((doc_counter, score))

                # Facet indices
                self.by_category[assigned_category].add(doc_counter)
                self.by_doc_type[dtype].add(doc_counter)
                for sp in specs:
                    self.by_specialty[sp].add(doc_counter)

                doc_counter += 1

        self.total_docs = doc_counter
        self.is_loaded = True
        self.load_duration_ms = (time.perf_counter() - start_time) * 1000.0
        return self.total_docs

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        doc_type: Optional[str] = None,
        specialty: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        if not self.is_loaded:
            return {
                "total": 0,
                "query_time_ms": 0.0,
                "results": [],
                "facets": {"categories": {}, "doc_types": {}, "specialties": {}}
            }

        # 1. Determine filter mask
        candidate_ids: Optional[Set[int]] = None
        if category:
            cat_matches = self.by_category.get(category, set())
            candidate_ids = set(cat_matches) if candidate_ids is None else candidate_ids & cat_matches
        if doc_type:
            type_matches = self.by_doc_type.get(doc_type, set())
            candidate_ids = set(type_matches) if candidate_ids is None else candidate_ids & type_matches
        if specialty:
            norm_sp = specialty.strip()
            sp_matches = self.by_specialty.get(norm_sp, set())
            candidate_ids = set(sp_matches) if candidate_ids is None else candidate_ids & sp_matches

        # 2. Tokenize and expand query
        q_clean = query.strip()
        if not q_clean:
            # Return filtered collection without text scoring
            all_ids = set(range(self.total_docs)) if candidate_ids is None else candidate_ids
            results = []
            for doc_id in sorted(all_ids)[:limit]:
                doc = self.documents[doc_id]
                res_dict = doc.to_dict()
                res_dict["score"] = 1.0
                res_dict["snippet"] = doc.file_name
                results.append(res_dict)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "total": len(all_ids),
                "query_time_ms": round(elapsed_ms, 3),
                "results": results,
                "facets": self._compute_facets(all_ids)
            }

        q_tokens = tokenize(q_clean)
        expanded_terms: Set[str] = set()
        for t in q_tokens:
            expanded_terms.add(t)
            expanded_terms.add(stem_word(t))
            if t in RUSSIAN_ABBREVIATIONS:
                for expansion in RUSSIAN_ABBREVIATIONS[t]:
                    expanded_terms.add(expansion)
                    expanded_terms.add(stem_word(expansion))

        # 3. Calculate BM25-style / TF-IDF scores
        scores: Dict[int, float] = defaultdict(float)
        matched_terms_per_doc: Dict[int, Set[str]] = defaultdict(set)

        for term in expanded_terms:
            postings = self.index.get(term, [])
            if not postings:
                continue
            idf = math.log(1.0 + (self.total_docs - len(postings) + 0.5) / (len(postings) + 0.5))
            idf = max(0.2, idf)
            for doc_id, tf_val in postings:
                if candidate_ids is not None and doc_id not in candidate_ids:
                    continue
                scores[doc_id] += tf_val * idf
                matched_terms_per_doc[doc_id].add(term)

        # Bonus for matching all original query tokens
        for doc_id in list(scores.keys()):
            doc = self.documents[doc_id]
            orig_matches = sum(1 for qt in q_tokens if qt in doc.tokens or stem_word(qt) in doc.stemmed_tokens)
            if orig_matches == len(q_tokens) and len(q_tokens) > 0:
                scores[doc_id] *= 2.5
            elif orig_matches > 0:
                scores[doc_id] *= (1.0 + 0.5 * orig_matches)

        # Sort descending by score
        ranked_doc_ids = sorted(scores.keys(), key=lambda d: scores[d], reverse=True)
        total_found = len(ranked_doc_ids)

        results = []
        for doc_id in ranked_doc_ids[:limit]:
            doc = self.documents[doc_id]
            res_dict = doc.to_dict()
            res_dict["score"] = round(scores[doc_id], 4)
            res_dict["snippet"] = self._generate_snippet(doc, q_tokens)
            results.append(res_dict)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "total": total_found,
            "query_time_ms": round(elapsed_ms, 3),
            "results": results,
            "facets": self._compute_facets(set(ranked_doc_ids))
        }

    def _generate_snippet(self, doc: NormativeDocument, query_tokens: List[str]) -> str:
        full_title = doc.file_name
        if not query_tokens:
            return full_title
        # Highlight matched terms with <mark> tags
        highlighted = full_title
        for qt in query_tokens:
            pattern = re.compile(re.escape(qt), re.IGNORECASE)
            highlighted = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", highlighted)
        return highlighted

    def _compute_facets(self, doc_ids: Set[int]) -> Dict[str, Dict[str, int]]:
        categories: Dict[str, int] = defaultdict(int)
        doc_types: Dict[str, int] = defaultdict(int)
        specialties: Dict[str, int] = defaultdict(int)

        for doc_id in doc_ids:
            doc = self.documents[doc_id]
            categories[doc.category] += 1
            doc_types[doc.doc_type] += 1
            for sp in doc.specialties:
                specialties[sp] += 1

        return {
            "categories": dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)),
            "doc_types": dict(sorted(doc_types.items(), key=lambda x: x[1], reverse=True)),
            "specialties": dict(sorted(specialties.items(), key=lambda x: x[1], reverse=True))
        }


# Global singleton instance for in-memory sub-10ms lookup
INDEX = InvertedIndex()


def get_normative_index(catalog_path: Optional[str] = None) -> InvertedIndex:
    global INDEX
    if not INDEX.is_loaded:
        if not catalog_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            catalog_path = os.path.join(base_dir, "data", "normative", "corpus_catalog.json")
        INDEX.load_from_catalog(catalog_path)
    return INDEX
