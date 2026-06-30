from abc import ABC, abstractmethod
from typing import Dict, List


class BaseExtractor(ABC):
    """
    Contract that every language extractor must satisfy.
    Each extractor reads a single source file and returns a list of
    artifact dicts following the standard schema defined in make_artifact().
    """

    BUSINESS_KEYWORDS: List[str] = [
        "validate", "validation", "verify", "check",
        "calculate", "calculation", "compute",
        "process", "apply", "execute", "handle",
        "create", "update", "delete", "save", "submit",
        "approve", "reject", "deny", "authorize",
        "notify", "send", "dispatch", "publish",
        "evaluate", "assess", "determine",
        "place", "cancel", "confirm", "complete",
        "assign", "allocate", "reserve",
        "charge", "refund", "discount", "price",
        "register", "enroll", "subscribe",
        "login", "logout", "authenticate",
        "generate", "build", "transform", "convert",
        "import", "export", "sync", "migrate",
        # keywords missing from original — caused genuine rules to be skipped
        "total",      # Order.Total()
        "remove",     # RemoveEmptyItems()
        "transfer",   # TransferBasketAsync()
        "aggregate",  # AggregateQuantity()
        "add",        # AddItem(), AddQuantity()
        "seed",       # SeedAsync()
    ]

    BUSINESS_CATEGORIES: Dict[str, List[str]] = {
        "validation": ["validate", "verify", "check", "isvalid", "can", "is_valid"],
        "calculation": [
            "calculate", "compute", "sum", "total", "price",
            "charge", "discount", "tax", "fee", "cost", "amount",
        ],
        "approval": ["approve", "reject", "authorize", "deny", "review", "submit"],
        "data_operation": [
            "create", "update", "delete", "save", "insert",
            "get", "find", "fetch", "search", "load", "read",
        ],
        "process": [
            "process", "execute", "run", "apply", "handle", "dispatch",
            "place", "cancel", "confirm", "complete", "finish",
            "remove", "transfer", "aggregate", "add", "seed",
        ],
        "notification": ["notify", "send", "email", "alert", "message", "publish"],
        "authentication": ["login", "logout", "authenticate", "authorize", "register"],
        "transformation": ["transform", "convert", "map", "serialize", "deserialize"],
        "integration": ["import", "export", "sync", "migrate", "push", "pull"],
    }

    # ── abstract interface ─────────────────────────────────────────────────────

    @abstractmethod
    def extract(self, file_path: str) -> List[Dict]:
        """Extract artifacts from a single file. Must be implemented."""
        pass

    # ── shared helpers ─────────────────────────────────────────────────────────

    def extract_all(self, files: List[str]) -> List[Dict]:
        """Run extract() on every file, swallowing per-file errors."""
        results: List[Dict] = []
        for file_path in files:
            try:
                results.extend(self.extract(file_path))
            except Exception as exc:
                print(f"  [warn] could not parse {file_path}: {exc}")
        return results

    def is_business_method(self, name: str) -> bool:
        lower = name.lower()
        return any(kw in lower for kw in self.BUSINESS_KEYWORDS)

    def get_business_category(self, name: str) -> str:
        lower = name.lower()
        for category, keywords in self.BUSINESS_CATEGORIES.items():
            if any(kw in lower for kw in keywords):
                return category
        return "general"

    def make_artifact(self, **kwargs) -> Dict:
        """Return a dict that follows the standard artifact schema."""
        return {
            "language": kwargs.get("language", "unknown"),
            "source_file": kwargs.get("source_file", ""),
            "type": kwargs.get("type", "unknown"),       # method | class | interface | enum | function | property
            "name": kwargs.get("name", ""),
            "content": kwargs.get("content", ""),
            "metadata": kwargs.get("metadata", {}),
            "is_business_artifact": kwargs.get("is_business_artifact", False),
            "business_category": kwargs.get("business_category", "general"),
        }
