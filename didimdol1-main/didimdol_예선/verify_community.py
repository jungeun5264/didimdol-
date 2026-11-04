"""오프라인 커뮤니티 DB 회귀 테스트 (서비스 DB/기존 사용자 데이터 변경 없음).

실행: python verify_community.py
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import store
import community_store as cs


def run():
    original = store.LOCAL_DB
    original_get_url = store._database_url
    with tempfile.TemporaryDirectory(prefix='didimdol-community-') as temp:
        store.LOCAL_DB = Path(temp) / 'test.sqlite3'
        store._database_url = lambda: ''
        try:
            store.initialize()
            alice = store.create_account('alice_test', '앨리스', 'test_hash')
            bob = store.create_account('bob_test', '밥', 'test_hash')
            assert alice and bob
            # 원래 모듈의 정상 DB 테이블은 유지됩니다.
            with store.connect() as conn:
                tables = {r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                assert {'users','diagnoses','training_attempts','lpa_type_profiles'} <= tables

            cs.ensure_schema()
            cs.ensure_schema()  # idempotent
            post = cs.create_post(alice['user_id'], '질문', 'AI 내용 검증 방법', 'AI 출처 검증을 어떻게 하나요?')
            detail = cs.get_post(post)
            assert detail['title'] == 'AI 내용 검증 방법'
            rows,total = cs.list_posts()
            assert total == 1 and rows[0]['post_id'] == post
            rows,total = cs.list_posts('질문', '검증')
            assert total == 1 and len(rows) == 1
            rows,total = cs.list_posts('학습 후기', '검증')
            assert total == 0
            rows,total = cs.list_posts('질문', '검색어없음')
            assert total == 0

            assert not cs.update_post(post, bob['user_id'], '질문', '변조 제목', '변조 내용')
            assert not cs.delete_post(post, bob['user_id'])
            assert cs.get_post(post)['title'] == 'AI 내용 검증 방법'
            assert cs.update_post(post, alice['user_id'], '정보 공유', 'AI 정보 검증 후기', '공식 출처를 확인했습니다.')
            assert cs.get_post(post)['category'] == '정보 공유'
            try:
                cs.create_post(alice['user_id'], '선택 불가능', '일반 제목', '본문 내용')
                raise AssertionError('invalid category accepted')
            except ValueError:
                pass
            try:
                cs.create_post(alice['user_id'], '질문', 'x', '본문 내용')
                raise AssertionError('invalid title accepted')
            except ValueError:
                pass

            cid = cs.create_comment(post, bob['user_id'], '좋은 의견이에요.')
            assert len(cs.list_comments(post)) == 1
            assert cs.list_posts()[0][0]['comment_count'] == 1
            assert not cs.delete_comment(cid, alice['user_id'])
            assert cs.delete_comment(cid, bob['user_id'])
            assert cs.list_comments(post) == []
            cid2=cs.create_comment(post, bob['user_id'], '두 번째 댓글')

            cs.report_post(post,bob['user_id'],'개인정보 노출')
            cs.report_post(post,bob['user_id'],'광고·도배')
            with store.connect() as conn:
                count=conn.execute('SELECT COUNT(*) AS n FROM community_reports WHERE post_id=?',(post,)).fetchone()['n']
                assert count == 1

            # 페이지네이션 / 정렬 안정성 / 기존 계정과 기록 보존
            for i in range(10):
                cs.create_post(bob['user_id'], '질문', f'추가 질문 {i}', '여기에 질문 내용')
            first,total = cs.list_posts(page=1,per_page=8)
            second,_ = cs.list_posts(page=2,per_page=8)
            assert total == 11 and len(first)==8 and len(second)==3
            assert {p['post_id'] for p in first}.isdisjoint({p['post_id'] for p in second})
            assert cs.delete_post(post,alice['user_id'])
            assert cs.get_post(post) is None
            with store.connect() as conn:
                assert conn.execute('SELECT COUNT(*) AS n FROM community_comments WHERE comment_id=?',(cid2,)).fetchone()['n']==0
                assert conn.execute('SELECT COUNT(*) AS n FROM community_reports WHERE post_id=?',(post,)).fetchone()['n']==0
                assert conn.execute('SELECT COUNT(*) AS n FROM users').fetchone()['n']==2
            print('커뮤니티 DB 테스트 14개 영역 통과 (임시 SQLite)')
        finally:
            store.LOCAL_DB = original
            store._database_url = original_get_url


if __name__=='__main__':
    run()
