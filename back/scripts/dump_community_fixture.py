"""
커뮤니티(위험구간 제보) 테스트 데이터를 fixture로 추출하는 스크립트.
실제 전화번호/이름 등 개인정보로 보이는 필드는 익명화해서 내보낸다.

사용법:
    python scripts/dump_community_fixture.py
"""

import os
import sys
import gzip
import json
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core import serializers
from accounts.models import User
from community.models import Post, Comment, PostLike, Follow

DEMO_USERNAMES = ['qhrud5264', 'poopoo', 'bggood', 'thdusdlsel']

# 익명화할 필드 (개인정보로 보이는 값 -> 빈 값/플레이스홀더)
SANITIZE_DEFAULTS = {
    'name': '',
    'phone': '01012341234',
    'sos_number': '01012341234',
    'email': 'demo@safeway.example',
}

# 테스트 중 좌표 입력이 생략돼 전부 동일한 값(대전 인근)으로 들어가 있던 것을
# 게시글 제목/주소에 맞는 실제 좌표로 교정한다.
COORD_OVERRIDES = {
    9: (37.5172, 127.0470),   # 강남구청역 인근
    8: (37.5008, 127.0369),   # 역삼역 5번 출구
    7: (37.5008, 127.0369),   # 역삼역 1번 출구
    6: (37.4981, 127.0280),   # 강남역 11번 출구
    5: (37.4981, 127.0280),   # 강남역 10번 출구
    4: (37.5717, 126.9768),   # 광화문 세종대로
    3: (37.5384, 126.9923),   # 이태원 경리단길
    2: (37.5554, 126.9360),   # 신촌 연세로
    1: (37.5571, 126.9237),   # 홍대입구역 2번 출구
}


def run():
    for pk, (lat, lng) in COORD_OVERRIDES.items():
        Post.objects.filter(pk=pk).update(latitude=lat, longitude=lng)

    users = list(User.objects.filter(username__in=DEMO_USERNAMES))
    posts = list(Post.objects.filter(user__in=users))
    comments = list(Comment.objects.filter(post__in=posts))
    likes = list(PostLike.objects.filter(post__in=posts))
    follows = list(Follow.objects.filter(follower__in=users, following__in=users))

    objects = users + posts + comments + likes + follows
    raw = serializers.serialize('json', objects)
    data = json.loads(raw)

    for obj in data:
        if obj['model'] == 'accounts.user':
            obj['fields'].update(SANITIZE_DEFAULTS)

    out_path = os.path.join(BASE_DIR, 'fixtures', 'community.json.gz')
    with gzip.open(out_path, 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'완료: 유저 {len(users)}명, 게시글 {len(posts)}건, 댓글 {len(comments)}건 -> {out_path}')


if __name__ == '__main__':
    run()
