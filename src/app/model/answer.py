import sqlite3
import typing
from typing import List, Optional

from telegram import User

from app.fs import DB_PATH

if typing.TYPE_CHECKING:
    from .poll import Poll


class Answer(object):
    def __init__(self, poll: 'Poll', text: str):
        self.id: Optional[int] = None
        self.text: str = text
        self._voters: List[User] = []
        self._poll: 'Poll' = poll

    def voters(self):
        """
        list of users who voted for this answer.

        Returns:
             List[User]
        """
        return self._voters

    def poll(self) -> 'Poll':
        """
        'many answers to one poll' reference.

        Returns:
            Poll: associated `Poll` instance.
        """
        return self._poll

    def store(self):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            # store answers
            if self.id is None:
                cur.execute("""INSERT INTO answers (poll_id, txt) VALUES (?, ?)""",
                            (self._poll.id, self.text))
                self.id = cur.lastrowid
            else:
                cur.execute("""UPDATE answers SET poll_id = ?, txt = ? WHERE id = ?""",
                            (self._poll.id, self.text, self.id))

            # store users
            for v in self.voters():
                cur.execute("""SELECT * FROM users WHERE id = ?""", (v.id,))

                if cur.fetchone() is None:
                    cur.execute("""
                        INSERT INTO users (id, first_name, last_name, username)
                        VALUES (?, ?, ?, ?)
                        """, (v.id, v.first_name, v.last_name, v.username))

                else:
                    cur.execute("""
                        UPDATE users
                        SET first_name = ?, last_name = ?, username = ?
                        WHERE id = ?
                        """, (v.first_name, v.last_name, v.username, v.id))

            # store connections
            # # remove all connection with this answer
            cur.execute("""DELETE FROM votes WHERE poll_id = ? AND answer_id = ?""",
                        (self.poll().id, self.id))

            # # store current voters
            for v in self.voters():
                cur.execute("""
                    INSERT INTO votes (user_id, poll_id, answer_id)
                    VALUES (?, ?, ?)
                    """, (v.id, self._poll.id, self.id))
            conn.commit()

        assert self.id is not None

    def __str__(self):
        # percentage for the answer is a ratio of this answer's voters to total unique voters count.

        total = self.poll().total_voters()
        count = len(self.voters())
        max_count: int = max(len(answer.voters()) for answer in self.poll().answers())
        relative_percentage: float = count / max_count if max_count != 0 else 0
        percentage: float = count / total if total != 0 else 0  # 0..1

        if count == 0:
            bar = "\u25AB 0%"
        else:
            bar = "{:\U0001f44d<{}} {}%".format(
                '',
                max(1, int(relative_percentage * 8)),
                int(percentage * 100))

        voters = ''
        if len(self.voters()):
            voters = '\n'
            voters += ', '.join(['[{}](tg://user?id={})'.format(voter.full_name, voter.id) for voter in self.voters()])

        return "{} \- {}\n{}{}".format(self.text, count, bar, voters)

    @classmethod
    def load(cls, poll: 'Poll', answer_id: int) -> Optional['Answer']:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""SELECT txt FROM answers WHERE poll_id = ? AND id = ?""",
                        (poll.id, answer_id))
            row: sqlite3.Row = cur.fetchone()

            if row is None:
                return

            text: str = row['txt']
            answer: Answer = cls(poll, text)
            answer.id = answer_id

            # next, load voters for this option

            cur.execute("""
                SELECT
                    u.id AS id,
                    u.first_name AS first_name,
                    u.last_name AS last_name,
                    u.username AS username
                FROM users u
                INNER JOIN
                (SELECT * FROM votes v WHERE v.poll_id = ? AND v.answer_id = ?) v
                ON u.id = v.user_id
                ORDER BY u.id DESC
                """, (poll.id, answer.id))

            for row in cur.fetchall():
                row: sqlite3.Row = row
                user = User(row['id'],
                            is_bot=False,
                            first_name=row['first_name'],
                            last_name=row['last_name'],
                            username=row['username'])
                answer._voters.append(user)

        return answer

    @classmethod
    def query(cls, poll: 'Poll') -> List['Answer']:
        """
        load from the database those answer which belong to poll with id == `poll.id`.

        :param poll: a poll object.
        :return: list of answers options for a given poll.
        """
        answers: List[Answer] = []

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT id
                FROM answers
                WHERE poll_id = ?
                ORDER BY id ASC
                """, (poll.id,))
            rows: List[sqlite3.Row] = cur.fetchall()

        for row in rows:
            answer_id: int = row['id']
            answers.append(cls.load(poll, answer_id))

        return answers
