from dataclasses import dataclass, field, asdict
from typing import List, Optional
import json

@dataclass
class Transaction:
    id: str
    type: str  # income / expense
    date: str  # YYYY-MM-DD
    amount: int
    category: str
    memo: Optional[str] = ""
    tags: List[str] = field(default_factory=list)

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        return cls(
            id=str(data['id']),
            type=data['type'],
            date=data['date'],
            amount=int(data['amount']),
            category=data['category'],
            memo=data.get('memo', ''),
            tags=data.get('tags', [])
        )

@dataclass
class Budget:
    month: str  # YYYY-MM
    amount: int