"""디딤돌 커뮤니티 게시판: 로그인 사용자 전용 Streamlit UI.

사용자 작성 문자열은 st.html/unsafe_allow_html을 사용하지 않고 출력합니다.
"""
from __future__ import annotations

import streamlit as st
import auth
import community_store as db


def _safe_error(exc):
    if isinstance(exc, ValueError):
        st.error(str(exc))
    else:
        st.error('처리 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.')


def _list_view(user_id):
    left, right = st.columns([4, 1])
    with left:
        st.subheader('게시글 목록')
    with right:
        if st.button('새 글 작성', type='primary', use_container_width=True):
            st.session_state['community_mode'] = 'write'
            st.rerun()

    a,b=st.columns([1,3])
    with a:
        category=st.selectbox('분류', ['전체', *db.CATEGORIES], key='community_filter')
    with b:
        term=st.text_input('검색', placeholder='제목 또는 본문에서 검색', key='community_search', max_chars=80)
    marker=(category,term)
    if st.session_state.get('community_last_filter') != marker:
        st.session_state['community_last_filter'] = marker
        st.session_state['community_page']=1
    page=int(st.session_state.get('community_page',1))
    try:
        posts,total=db.list_posts(category,term,page)
    except Exception as exc:
        _safe_error(exc)
        return
    st.caption(f'게시글 {total}개')
    if not posts:
        st.info('등록된 게시글이 없습니다. 첫 글을 작성해보세요.')
    for post in posts:
        with st.container(border=True):
            cols=st.columns([4,1],vertical_alignment='center')
            with cols[0]:
                st.write(f"[{post['category']}] {post['title']}")
                st.caption(f"{post['author']} · {post['created_at']} · 댓글 {post['comment_count']}개")
            with cols[1]:
                if st.button('읽기',key=f"community_open_{post['post_id']}",use_container_width=True):
                    st.session_state['community_post_id']=post['post_id']
                    st.session_state['community_mode']='read'
                    st.rerun()
    max_page=max(1,(total+db.PAGE_SIZE-1)//db.PAGE_SIZE)
    if page>max_page:
        st.session_state['community_page']=max_page
        st.rerun()
    c1,c2,c3=st.columns([1,2,1],vertical_alignment='center')
    with c1:
        if st.button('이전', disabled=page<=1, use_container_width=True):
            st.session_state['community_page']=page-1
            st.rerun()
    with c2:
        st.caption(f'{page} / {max_page} 페이지')
    with c3:
        if st.button('다음',disabled=page>=max_page,use_container_width=True):
            st.session_state['community_page']=page+1
            st.rerun()


def _write_view(user_id):
    if st.button('목록으로 돌아가기',key='community_back_write'):
        st.session_state['community_mode']='list'
        st.rerun()
    st.subheader('글 작성')
    with st.form('community_create_form', clear_on_submit=False):
        category=st.selectbox('카테고리',db.CATEGORIES)
        title=st.text_input('제목',max_chars=100)
        content=st.text_area('내용',height=220,max_chars=5000)
        submitted=st.form_submit_button('등록하기',type='primary')
    if submitted:
        try:
            post_id=db.create_post(user_id,category,title,content)
        except Exception as exc:
            _safe_error(exc)
        else:
            st.session_state['community_post_id']=post_id
            st.session_state['community_mode']='read'
            st.rerun()


def _edit_view(post,user_id):
    if st.button('글로 돌아가기',key='community_edit_back'):
        st.session_state['community_mode']='read'
        st.rerun()
    st.subheader('글 수정')
    with st.form('community_edit_form'):
        category=st.selectbox('카테고리',db.CATEGORIES,index=db.CATEGORIES.index(post['category']))
        title=st.text_input('제목',value=post['title'],max_chars=100)
        content=st.text_area('내용',value=post['content'],height=220,max_chars=5000)
        submitted=st.form_submit_button('수정 저장',type='primary')
    if submitted:
        try:
            ok=db.update_post(post['post_id'],user_id,category,title,content)
            if not ok:
                st.error('작성자만 수정할 수 있습니다.')
                return
        except Exception as exc:
            _safe_error(exc)
        else:
            st.session_state['community_mode']='read'
            st.rerun()


def _read_view(user_id):
    post_id=st.session_state.get('community_post_id')
    if not post_id:
        st.session_state['community_mode']='list'
        st.rerun()
    post=db.get_post(post_id)
    if not post:
        st.info('게시글을 찾을 수 없어요. 삭제되었을 수 있습니다.')
        if st.button('목록 보기',key='community_not_found'):
            st.session_state['community_mode']='list'
            st.rerun()
        return
    if st.button('목록으로',key='community_back_read'):
        st.session_state['community_mode']='list'
        st.rerun()
    with st.container(border=True):
        st.caption(post['category'])
        st.subheader(post['title'])
        st.caption(f"작성자: {post['author']} · 작성: {post['created_at']}")
        st.text(post['content'])
        if user_id == post['user_id']:
            col1,col2=st.columns(2)
            with col1:
                if st.button('글 수정',key='community_edit_post'):
                    st.session_state['community_mode']='edit'
                    st.rerun()
            with col2:
                confirm=st.checkbox('삭제 확인',key=f'community_delete_confirm_{post_id}')
                if st.button('글 삭제',disabled=not confirm,key='community_delete_post'):
                    if db.delete_post(post_id,user_id):
                        st.session_state['community_mode']='list'
                        st.session_state.pop('community_post_id',None)
                        st.rerun()
                    st.error('작성자만 삭제할 수 있습니다.')

    st.subheader('댓글')
    comments=db.list_comments(post_id)
    st.caption(f'{len(comments)}개')
    for comment in comments:
        with st.container(border=True):
            st.caption(f"{comment['author']} · {comment['created_at']}")
            st.text(comment['content'])
            if comment['user_id']==user_id:
                if st.button('댓글 삭제',key=f"community_delete_comment_{comment['comment_id']}"):
                    if db.delete_comment(comment['comment_id'],user_id):
                        st.rerun()
                    st.error('작성자만 댓글을 삭제할 수 있습니다.')
    with st.form(f'community_comment_form_{post_id}',clear_on_submit=True):
        text=st.text_area('댓글 작성',max_chars=500,height=100)
        submitted=st.form_submit_button('댓글 등록')
    if submitted:
        try:
            db.create_comment(post_id,user_id,text)
        except Exception as exc:
            _safe_error(exc)
        else:
            st.rerun()

    if post['user_id'] != user_id:
        with st.expander('게시글 신고'):
            reason=st.selectbox('신고 사유', db.REPORT_REASONS)
            if st.button('신고 접수',key=f'community_report_{post_id}'):
                try:
                    db.report_post(post_id,user_id,reason)
                except Exception as exc:
                    _safe_error(exc)
                else:
                    st.success('신고 내용이 저장되었습니다. 운영자 검토 기능은 별도 구축이 필요합니다.')


def render(navigate):
    user=auth.current_user()
    if not user:
        navigate('login')
        return
    try:
        db.ensure_schema()
    except Exception:
        st.error('커뮤니티 데이터 저장소를 준비하지 못했습니다. DATABASE_URL과 권한을 확인해주세요.')
        return
    st.title('디딤돌 커뮤니티')
    st.caption('AI 활용 질문, 학습 후기, 유용한 정보를 공유하는 공간입니다.')
    st.info('실명·연락처·비밀번호·API 키·타인의 개인정보를 게시하지 마세요.')
    mode=st.session_state.get('community_mode','list')
    if mode=='write':
        _write_view(user['user_id'])
    elif mode=='read':
        _read_view(user['user_id'])
    elif mode=='edit':
        post=db.get_post(st.session_state.get('community_post_id',''))
        if post and post['user_id']==user['user_id']:
            _edit_view(post,user['user_id'])
        else:
            st.error('작성자만 수정할 수 있습니다.')
            st.session_state['community_mode']='list'
    else:
        _list_view(user['user_id'])
