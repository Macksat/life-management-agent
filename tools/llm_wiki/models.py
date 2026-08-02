"""LLMWiki のデータモデル定義。

spec: docs/llm_wiki.md
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceRef:
    """Wiki page が依拠する元ソース参照。"""

    source_type: str
    source_path: str
    anchor: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WikiLink:
    """Page 間の関係。"""

    relation: str
    target_page_id: str
    target_path: str
    confidence: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WikiPage:
    """Compiled wiki page。"""

    page_id: str
    page_type: str
    title: str
    path: str
    summary: str
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    links: list[WikiLink] = field(default_factory=list)
    source_refs: list[SourceRef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    key_facts: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "page_type": self.page_type,
            "title": self.title,
            "path": self.path,
            "summary": self.summary,
            "tags": self.tags,
            "aliases": self.aliases,
            "links": [link.to_dict() for link in self.links],
            "source_refs": [ref.to_dict() for ref in self.source_refs],
            "metadata": self.metadata,
            "key_facts": self.key_facts,
            "open_questions": self.open_questions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WikiPage":
        return cls(
            page_id=data["page_id"],
            page_type=data["page_type"],
            title=data["title"],
            path=data["path"],
            summary=data.get("summary", ""),
            tags=list(data.get("tags", [])),
            aliases=list(data.get("aliases", [])),
            links=[WikiLink(**item) for item in data.get("links", [])],
            source_refs=[SourceRef(**item) for item in data.get("source_refs", [])],
            metadata=dict(data.get("metadata", {})),
            key_facts=list(data.get("key_facts", [])),
            open_questions=list(data.get("open_questions", [])),
        )


@dataclass
class WikiSearchResult:
    """Wiki 検索結果。"""

    page_id: str
    page_type: str
    title: str
    path: str
    score: float
    reason: str
    summary: str
    tags: list[str] = field(default_factory=list)


@dataclass
class ValidationIssue:
    """Validation で見つかった問題。"""

    code: str
    path: str
    message: str


@dataclass
class ValidationReport:
    """Validation 結果。"""

    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    repaired: list[str] = field(default_factory=list)


@dataclass
class IssueSnapshot:
    """GitHub Issue snapshot。"""

    number: int
    title: str
    body: str
    state: str
    url: str
    labels: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)


@dataclass
class MemoryRecord:
    """Normalized source record used to build LLMWiki pages."""

    id: str
    layer: str
    source_path: str
    title: str = ""
    text: str = ""
    summary: str = ""
    tags: str = ""
    section: str = ""
    date: str = ""
    recency_bucket: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CoReference:
    """Conversation-time co-reference log entry."""

    pages: list[str]
    query_intent: str
    timestamp: str
    conversation_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoReference":
        return cls(
            pages=list(data["pages"]),
            query_intent=data["query_intent"],
            timestamp=data["timestamp"],
            conversation_id=data.get("conversation_id", "unknown"),
        )
