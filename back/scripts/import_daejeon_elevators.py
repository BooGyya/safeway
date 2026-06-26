"""
대전교통공사 엘리베이터 위치정보 import 스크립트

사용법:
    python manage.py shell < scripts/import_daejeon_elevators.py
또는:
    python scripts/import_daejeon_elevators.py (Django 환경 설정 필요)

CSV 파일 경로를 아래 CSV_PATH에 맞게 수정하세요.
"""

import os
import sys
import django

# Django 환경 설정 (manage.py shell 사용 시 불필요)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import csv
from infrastructure.models import Elevator

# CSV 파일 경로 (실제 경로로 수정)
CSV_PATH = r'C:\Users\user\OneDrive\바탕 화면\safewayaa\대전교통공사_엘리베이터 위치정보_20241231.csv'
def run():
    created_count = 0
    skipped_count = 0

    with open(CSV_PATH, encoding='cp949') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row['위도']) if row['위도'] else None
                lng = float(row['경도']) if row['경도'] else None
            except ValueError:
                print(f"  좌표 오류 스킵: {row}")
                skipped_count += 1
                continue

            # 중복 방지: 역사명 + 호기로 체크
            exists = Elevator.objects.filter(
                building_nm=row['역사'],
                install_place=row['설치위치'],
                sigungu=row['호기'],
            ).exists()

            if exists:
                skipped_count += 1
                continue

            Elevator.objects.create(
                building_nm=row['역사'],          # 역사명
                sido='대전',
                sigungu=row['호기'],              # 호기 (번호) → sigungu 임시 활용
                address=f"대전 {row['역사']}",
                lat=lat,
                lng=lng,
                elevator_type=row['내외'],         # 내부/외부
                install_place=row['설치위치'],      # 설치위치
                is_operating=True,
            )
            created_count += 1
            print(f"  ✅ {row['역사']} {row['호기']}호기 ({row['설치위치']}) 삽입")

    print(f"\n완료: {created_count}개 삽입, {skipped_count}개 스킵")

if __name__ == '__main__':
    run()