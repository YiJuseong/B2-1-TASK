import os
import json
import tempfile
from typing import Generator, List, Dict
from budget_app.models import Transaction, Budget

class DataRepository:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.tx_path = os.path.join(data_dir, "transactions.jsonl")
        self.cat_path = os.path.join(data_dir, "categories.jsonl")
        self.bg_path = os.path.join(data_dir, "budgets.jsonl")
        
        self._init_files()

    def _init_files(self):
        # 파일이 없을 시 자동 생성 및 기본 카테고리 로드(안 A)
        if not os.path.exists(self.cat_path):
            self.save_categories(["food", "transport", "rent", "etc"])
        if not os.path.exists(self.tx_path):
            with open(self.tx_path, 'w', encoding='utf-8') as f: pass
        if not os.path.exists(self.bg_path):
            with open(self.bg_path, 'w', encoding='utf-8') as f: pass

    # --- Categories ---
    def load_categories(self) -> List[str]:
        if not os.path.exists(self.cat_path): return []
        with open(self.cat_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    def save_categories(self, categories: List[str]):
        # 원자적 파일 쓰기
        with tempfile.NamedTemporaryFile('w', dir=self.data_dir, delete=False, encoding='utf-8') as tf:
            for cat in categories:
                tf.write(f"{cat}\n")
            temp_name = tf.name
        os.replace(temp_name, self.cat_path)

    # --- Budgets ---
    def load_budgets(self) -> Dict[str, int]:
        budgets = {}
        if not os.path.exists(self.bg_path): return budgets
        with open(self.bg_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    budgets[data['month']] = data['amount']
        return budgets

    def save_budget(self, month: str, amount: int):
        budgets = self.load_budgets()
        budgets[month] = amount
        with tempfile.NamedTemporaryFile('w', dir=self.data_dir, delete=False, encoding='utf-8') as tf:
            for m, a in budgets.items():
                tf.write(json.dumps({"month": m, "amount": a}) + "\n")
            temp_name = tf.name
        os.replace(temp_name, self.bg_path)

    # --- Transactions (Streaming Generator) ---
    def stream_transactions(self) -> Generator[Transaction, None, None]:
        if not os.path.exists(self.tx_path): return
        with open(self.tx_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    yield Transaction.from_dict(json.loads(line))

    def add_transaction(self, tx: Transaction):
        with open(self.tx_path, 'a', encoding='utf-8') as f:
            f.write(tx.to_jsonl() + "\n")

    def rewrite_transactions(self, transactions: List[Transaction]):
        with tempfile.NamedTemporaryFile('w', dir=self.data_dir, delete=False, encoding='utf-8') as tf:
            for tx in transactions:
                tf.write(tx.to_jsonl() + "\n")
            temp_name = tf.name
        os.replace(temp_name, self.tx_path)