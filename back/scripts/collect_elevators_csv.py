import os
import sys
import django
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from infrastructure.models import Elevator

CSV_DIR = 'C:/Users/SSAFY/Downloads/한국승강기안전공단_승강기 설치 현황_20251231'

def collect():
    print("승강기 데이터 수집 시작 (서울+대전)...")

    df1 = pd.read_csv(f'{CSV_DIR}/한국승강기안전공단_승강기 설치 현황_2016년 이후.csv', encoding='utf-8')
    df2 = pd.read_csv(f'{CSV_DIR}/한국승강기안전공단_승강기 설치 현황_2015년 이전.csv', encoding='utf-8')
    df = pd.concat([df1, df2], ignore_index=True)

    target_kinds = ['장애인용', '장애/병원용', '장애/승객화물용', '소방구조/장애인용', '장애/전망용']
    target_types = ['휠체어리프트', '경사형엘리베이터']

    filtered = df[
        (df['승강기상태'] == '운행중') &
        (df['승강기종류'].isin(target_kinds) | df['승강기구분'].isin(target_types)) &
        (df['시도'].isin(['서울', '대전']))
    ].drop_duplicates(subset=['건물주소'])

    print(f"필터링 완료: {len(filtered)}건")

    # 기존 데이터 삭제
    Elevator.objects.all().delete()
    print("기존 데이터 삭제 완료")

    # DB 저장
    objs = []
    for _, row in filtered.iterrows():
        objs.append(Elevator(
            building_nm=str(row['건물명']) if pd.notna(row['건물명']) else '',
            sido=str(row['시도']) if pd.notna(row['시도']) else '',
            sigungu=str(row['시군구']) if pd.notna(row['시군구']) else '',
            address=str(row['건물주소']) if pd.notna(row['건물주소']) else '',
            lat=None,
            lng=None,
            elevator_type=str(row['승강기구분']) if pd.notna(row['승강기구분']) else '',
            is_operating=True,
            install_place=str(row['설치장소']) if pd.notna(row['설치장소']) else '',
        ))

    Elevator.objects.bulk_create(objs, batch_size=1000)
    print(f"DB 저장 완료! {Elevator.objects.count()}건")

if __name__ == '__main__':
    collect()