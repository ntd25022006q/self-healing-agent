import sqlite3
import datetime
from config import Config


class MemoryDB:
    @classmethod
    def get_connection(cls):
        db_path = Config.MEMORY_DB_PATH
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def init_db(cls):
        """
        Create tables if they don't exist.
        """
        conn = cls.get_connection()
        cursor = conn.cursor()

        # Experiences table stores bug fixing and learning patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_description TEXT,
                error_message TEXT,
                fix_code TEXT,
                score INTEGER,
                created_at TEXT
            )
        """)

        # Agent score tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_score (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_score INTEGER DEFAULT 100
            )
        """)

        # Initialize default agent score if table is empty
        cursor.execute("SELECT current_score FROM agent_score WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO agent_score (id, current_score) VALUES (1, 100)")

        conn.commit()
        conn.close()

    @classmethod
    def save_experience(cls, task_desc: str, error_msg: str, fix_code: str, score: int = 100):
        """
        Save a successful self-healing experience to database.
        """
        cls.init_db()
        conn = cls.get_connection()
        cursor = conn.cursor()

        now = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO experiences (task_description, error_message, fix_code, score, created_at) VALUES (?, ?, ?, ?, ?)",
            (task_desc, error_msg, fix_code, score, now)
        )
        conn.commit()
        conn.close()

    @classmethod
    def query_similar_experiences(cls, query_text: str, limit: int = 2) -> list:
        """
        Performs keyword-based similarity search to fetch related past experiences,
        ranking them by actual keyword overlap count to avoid noise.
        """
        cls.init_db()
        conn = cls.get_connection()
        cursor = conn.cursor()

        # Define stop words to filter out common noise
        stop_words = {
            "error", "exception", "traceback", "line", "file", "import", "from",
            "class", "def", "return", "module", "object", "none", "true", "false",
            "test", "tests", "passed", "failed", "timeout", "during", "call", "in"
        }

        import re
        # Tokenize query text and filter words
        query_words = set(
            w.lower().strip()
            for w in re.findall(r"\b\w{3,}\b", query_text)
            if w.lower().strip() not in stop_words
        )

        if not query_words:
            conn.close()
            return []

        try:
            # Fetch the last 100 experiences to rank them in Python
            cursor.execute(
                "SELECT * FROM experiences ORDER BY id DESC LIMIT 100")
            rows = cursor.fetchall()
            conn.close()

            ranked_results = []
            for r in rows:
                task_desc = r["task_description"] or ""
                err_msg = r["error_message"] or ""

                # Tokenize fields
                field_words = set(
                    w.lower().strip()
                    for w in re.findall(r"\b\w{3,}\b", task_desc + " " + err_msg)
                )

                # Calculate keyword overlap
                overlap = len(query_words.intersection(field_words))
                if overlap > 0:
                    ranked_results.append((overlap, {
                        "task_description": task_desc,
                        "error_message": err_msg,
                        "fix_code": r["fix_code"],
                        "score": r["score"]
                    }))

            # Sort by overlap score descending, then by DB id/recency
            ranked_results.sort(key=lambda x: x[0], reverse=True)

            # Return top matches
            return [item[1] for item in ranked_results[:limit]]
        except Exception as e:
            print(f"[MemoryDB] Search error: {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            return []

    @classmethod
    def get_agent_score(cls) -> int:
        """
        Retrieve current agent performance score.
        """
        cls.init_db()
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT current_score FROM agent_score WHERE id = 1")
        row = cursor.fetchone()
        score = row["current_score"] if row else 100
        conn.close()
        return score

    @classmethod
    def update_agent_score(cls, change: int) -> int:
        """
        Increment or decrement agent score, keeping it database persistent.
        """
        cls.init_db()
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE agent_score SET current_score = current_score + ? WHERE id = 1", (change,))
        conn.commit()

        cursor.execute("SELECT current_score FROM agent_score WHERE id = 1")
        row = cursor.fetchone()
        new_score = row["current_score"] if row else 100
        conn.close()
        return new_score


if __name__ == "__main__":
    # Test DB init
    MemoryDB.init_db()
    print("Initial Score:", MemoryDB.get_agent_score())
    MemoryDB.update_agent_score(15)
    print("Score after reward (+15):", MemoryDB.get_agent_score())
    MemoryDB.update_agent_score(-30)
    print("Score after penalty (-30):", MemoryDB.get_agent_score())

    # Save a test experience
    MemoryDB.save_experience(
        "Read file config without os import",
        "NameError: name 'os' is not defined",
        "import os\n\ndef read_config():\n    return os.path.exists('config.py')"
    )

    similar = MemoryDB.query_similar_experiences("os NameError reading file")
    print("Similar past experiences:")
    print(similar)
