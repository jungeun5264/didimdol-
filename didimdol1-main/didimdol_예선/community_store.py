"""디딤돌 커뮤니티 저장소.

기존 store.connect()를 재사용하므로 SQLite/ PostgreSQL 설정과 사용자 테이블을 보존합니다.
게시글과 댓글의 수정·삭제는 user_id를 WHERE 절에 포함해 서버 측에서 권한을 검사합니다.
"""
from __future__ import annotations

import uuid
import store

CATEGORIES = ('질문', '학습 후기', '정보 공유')
REPORT_REASONS = ('광고·도배', '개인정보 노출', '욕설·괴롭힘', '기타')
PAGE_SIZE = 8


def _sql(conn, statement, values=()):
    # store._execute가 기존 프로젝트의 SQLite/PostgreSQL 파라미터 변환을 담당합니다.
    return store._execute(conn, statement, values)


def ensure_schema():
    """커뮤니티 페이지를 열면 최초 1회 생성 가능한 스키마를 점검합니다."""
    with store.connect() as conn:
        _sql(conn, '''CREATE TABLE IF NOT EXISTS community_posts (
            post_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        _sql(conn, '''CREATE TABLE IF NOT EXISTS community_comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL REFERENCES community_posts(post_id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        _sql(conn, '''CREATE TABLE IF NOT EXISTS community_reports (
            report_id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL REFERENCES community_posts(post_id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (post_id, user_id)
        )''')
        _sql(conn, 'CREATE INDEX IF NOT EXISTS idx_community_posts_created ON community_posts (created_at)')
        _sql(conn, 'CREATE INDEX IF NOT EXISTS idx_community_comments_post ON community_comments (post_id)')
        _sql(conn, 'CREATE INDEX IF NOT EXISTS idx_community_reports_status ON community_reports (status)')


def _validate_post(category, title, content):
    if category not in CATEGORIES:
        raise ValueError('올바른 게시글 분류를 선택해주세요.')
    title = title.strip()
    content = content.strip()
    if not (2 <= len(title) <= 100):
        raise ValueError('제목은 2~100자로 입력해주세요.')
    if not (2 <= len(content) <= 5000):
        raise ValueError('본문은 2~5,000자로 입력해주세요.')
    return category, title, content


def _validate_comment(content):
    content = content.strip()
    if not (1 <= len(content) <= 500):
        raise ValueError('댓글은 1~500자로 입력해주세요.')
    return content


def create_post(user_id, category, title, content):
    category, title, content = _validate_post(category, title, content)
    post_id = uuid.uuid4().hex
    with store.connect() as conn:
        _sql(conn, '''INSERT INTO community_posts (post_id,user_id,category,title,content)
                     VALUES (?,?,?,?,?)''', (post_id, user_id, category, title, content))
    return post_id


def update_post(post_id, user_id, category, title, content):
    category, title, content = _validate_post(category, title, content)
    with store.connect() as conn:
        result = _sql(conn, '''UPDATE community_posts SET category=?,title=?,content=?,
                           updated_at=CURRENT_TIMESTAMP WHERE post_id=? AND user_id=?''',
                      (category, title, content, post_id, user_id))
        return result.rowcount == 1


def delete_post(post_id, user_id):
    with store.connect() as conn:
        result = _sql(conn, 'DELETE FROM community_posts WHERE post_id=? AND user_id=?',
                      (post_id, user_id))
        return result.rowcount == 1


def get_post(post_id):
    with store.connect() as conn:
        row = _sql(conn, '''SELECT p.post_id,p.user_id,p.category,p.title,p.content,
                           p.created_at,p.updated_at,u.display_name AS author
                           FROM community_posts p JOIN users u ON u.user_id=p.user_id
                           WHERE p.post_id=?''', (post_id,)).fetchone()
        return dict(row) if row else None


def _where(category=None, keyword=''):
    filters = []
    args = []
    if category in CATEGORIES:
        filters.append('p.category=?')
        args.append(category)
    elif category not in (None, '전체'):
        raise ValueError('존재하지 않는 게시판 분류입니다.')
    term = (keyword or '').strip()
    if term:
        if len(term) > 80:
            raise ValueError('검색어는 최대 80자까지 입력할 수 있습니다.')
        filters.append('(LOWER(p.title) LIKE ? OR LOWER(p.content) LIKE ?)')
        like_term = f'%{term.lower()}%'
        args.extend([like_term, like_term])
    return (' WHERE ' + ' AND '.join(filters)) if filters else '', tuple(args)


def list_posts(category='전체', keyword='', page=1, per_page=PAGE_SIZE):
    page = max(1, int(page))
    per_page = max(1, min(30, int(per_page)))
    where, args = _where(category, keyword)
    with store.connect() as conn:
        total = _sql(conn, 'SELECT COUNT(*) AS n FROM community_posts p' + where,
                     args).fetchone()['n']
        rows = _sql(conn, '''SELECT p.post_id,p.user_id,p.category,p.title,p.created_at,
                        u.display_name AS author,
                        (SELECT COUNT(*) FROM community_comments c WHERE c.post_id=p.post_id) AS comment_count
                        FROM community_posts p JOIN users u ON p.user_id=u.user_id''' + where +
                    ' ORDER BY p.created_at DESC,p.post_id DESC LIMIT ? OFFSET ?',
                    (*args, per_page, (page-1)*per_page)).fetchall()
        return [dict(row) for row in rows], int(total)


def create_comment(post_id, user_id, content):
    content = _validate_comment(content)
    comment_id = uuid.uuid4().hex
    with store.connect() as conn:
        _sql(conn, '''INSERT INTO community_comments (comment_id,post_id,user_id,content)
                     VALUES (?,?,?,?)''', (comment_id, post_id, user_id, content))
    return comment_id


def list_comments(post_id):
    with store.connect() as conn:
        rows = _sql(conn, '''SELECT c.comment_id,c.post_id,c.user_id,c.content,c.created_at,
                        u.display_name AS author
                        FROM community_comments c JOIN users u ON u.user_id=c.user_id
                        WHERE c.post_id=? ORDER BY c.created_at,c.comment_id''',
                    (post_id,)).fetchall()
        return [dict(row) for row in rows]


def delete_comment(comment_id, user_id):
    with store.connect() as conn:
        result = _sql(conn, 'DELETE FROM community_comments WHERE comment_id=? AND user_id=?',
                      (comment_id, user_id))
        return result.rowcount == 1


def report_post(post_id, user_id, reason):
    if reason not in REPORT_REASONS:
        raise ValueError('신고 사유가 올바르지 않습니다.')
    with store.connect() as conn:
        _sql(conn, '''INSERT INTO community_reports (report_id,post_id,user_id,reason)
                     VALUES (?,?,?,?) ON CONFLICT(post_id,user_id) DO UPDATE SET
                     reason=excluded.reason, status='open', updated_at=CURRENT_TIMESTAMP''',
             (uuid.uuid4().hex, post_id, user_id, reason))
