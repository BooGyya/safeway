<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
</script>

<template>
  <div class="landing">
    <!-- 히어로 섹션 -->
    <section class="hero">
      <div class="hero-content">
        <img src="@/assets/logo.png" alt="SafeWay" class="hero-logo" />
        <h1>모두를 위한 안전한 길</h1>
        <p class="hero-desc">
          교통약자를 위한 맞춤형 안전 경로 추천 서비스<br />
          휠체어, 노인, 임산부 누구나 안심하고 이동할 수 있도록
        </p>
        <div class="hero-buttons">
          <button class="hero-btn primary" @click="router.push('/map')">지도 바로가기</button>
          <button v-if="!auth.isLoggedIn" class="hero-btn secondary" @click="router.push('/login')">로그인</button>
        </div>
      </div>
    </section>

    <!-- 기능 소개 -->
    <section class="features">
      <h2>SafeWay가 제공하는 기능</h2>
      <div class="feature-grid">
        <div class="feature-card">
          <span class="feature-icon">🗺️</span>
          <h3>맞춤 경로 추천</h3>
          <p>추천 / 계단회피 / 큰길우선 / 날씨반영<br />4가지 경로를 한눈에 비교하세요</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">♿</span>
          <h3>교통약자 유형별 안내</h3>
          <p>휠체어, 노인, 장애인, 임산부<br />유형에 맞는 보행속도와 안전경로</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">🚦</span>
          <h3>신호등 & 편의시설</h3>
          <p>음향신호기, 잔여시간 표시기<br />경로 주변 병원, 약국, 복지시설 안내</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">⚠️</span>
          <h3>위험구간 제보</h3>
          <p>커뮤니티 제보 기반 위험구간 표시<br />공사, 장애물, 파손 구간을 미리 확인</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">🤖</span>
          <h3>AI 챗봇</h3>
          <p>경로, 시설, 서비스 관련<br />궁금한 점을 AI에게 물어보세요</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">🆘</span>
          <h3>SOS 긴급 호출</h3>
          <p>위급 상황에 한 번의 터치로<br />등록된 비상연락처에 문자 발송</p>
        </div>
      </div>
    </section>

    <!-- 사용 방법 -->
    <section class="how-it-works">
      <h2>이렇게 사용하세요</h2>
      <div class="steps">
        <div class="step">
          <div class="step-num">1</div>
          <h3>출발지 & 도착지 입력</h3>
          <p>검색 또는 지도 클릭으로 위치를 설정하세요</p>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <div class="step-num">2</div>
          <h3>경로 비교 & 선택</h3>
          <p>4가지 경로를 비교하고 나에게 맞는 길을 선택하세요</p>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <div class="step-num">3</div>
          <h3>안전하게 이동</h3>
          <p>주변 시설과 위험구간을 확인하며 이동하세요</p>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta">
      <h2>지금 바로 안전한 길을 찾아보세요</h2>
      <p>교통약자도, 누구나 안심하고 걸을 수 있는 세상</p>
      <button class="hero-btn primary" @click="router.push('/map')">SafeWay 시작하기</button>
    </section>

    <!-- 푸터 -->
    <footer class="landing-footer">
      <p>SafeWay &copy; 2026 - 모두를 위한 안전한 길</p>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  font-family: 'Poppins', 'Noto Sans KR', sans-serif;
  color: #333;
}

/* 히어로 */
.hero {
  background: linear-gradient(135deg, #e6f7ee 0%, #f0faf5 50%, #ffffff 100%);
  padding: 80px 24px 60px;
  text-align: center;
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero-content {
  max-width: 600px;
}
.hero-logo {
  width: 200px;
  height: auto;
  margin-bottom: 24px;
}
.hero h1 {
  font-size: 36px;
  font-weight: 800;
  color: #1a1a1a;
  margin: 0 0 16px;
  line-height: 1.3;
}
.hero-desc {
  font-size: 17px;
  color: #666;
  line-height: 1.7;
  margin: 0 0 32px;
}
.hero-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}
.hero-btn {
  padding: 14px 32px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}
.hero-btn.primary {
  background: #2eb872;
  color: white;
  box-shadow: 0 4px 14px rgba(46,184,114,0.3);
}
.hero-btn.primary:hover {
  background: #259a60;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(46,184,114,0.4);
}
.hero-btn.secondary {
  background: white;
  color: #2eb872;
  border: 2px solid #2eb872;
}
.hero-btn.secondary:hover {
  background: #e6f7ee;
}

/* 기능 소개 */
.features {
  padding: 80px 24px;
  max-width: 1100px;
  margin: 0 auto;
  text-align: center;
}
.features h2 {
  font-size: 28px;
  font-weight: 800;
  color: #1a1a1a;
  margin: 0 0 48px;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}
.feature-card {
  background: white;
  border-radius: 16px;
  padding: 32px 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  transition: all 0.2s;
  text-align: center;
}
.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
}
.feature-icon {
  font-size: 40px;
  display: block;
  margin-bottom: 16px;
}
.feature-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: #222;
  margin: 0 0 8px;
}
.feature-card p {
  font-size: 14px;
  color: #888;
  line-height: 1.6;
  margin: 0;
}

/* 사용 방법 */
.how-it-works {
  padding: 80px 24px;
  background: #f8faf9;
  text-align: center;
}
.how-it-works h2 {
  font-size: 28px;
  font-weight: 800;
  color: #1a1a1a;
  margin: 0 0 48px;
}
.steps {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24px;
  max-width: 900px;
  margin: 0 auto;
}
.step {
  flex: 1;
  background: white;
  border-radius: 16px;
  padding: 32px 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  text-align: center;
}
.step-num {
  width: 44px;
  height: 44px;
  background: #2eb872;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
  margin: 0 auto 16px;
}
.step h3 {
  font-size: 16px;
  font-weight: 700;
  color: #222;
  margin: 0 0 8px;
}
.step p {
  font-size: 13px;
  color: #888;
  line-height: 1.5;
  margin: 0;
}
.step-arrow {
  font-size: 24px;
  color: #2eb872;
  font-weight: 700;
}

/* CTA */
.cta {
  padding: 80px 24px;
  text-align: center;
  background: linear-gradient(135deg, #2eb872, #259a60);
  color: white;
}
.cta h2 {
  font-size: 28px;
  font-weight: 800;
  margin: 0 0 12px;
}
.cta p {
  font-size: 16px;
  opacity: 0.9;
  margin: 0 0 32px;
}
.cta .hero-btn.primary {
  background: white;
  color: #2eb872;
  box-shadow: 0 4px 14px rgba(0,0,0,0.15);
}
.cta .hero-btn.primary:hover {
  background: #f0faf5;
  transform: translateY(-2px);
}

/* 푸터 */
.landing-footer {
  padding: 24px;
  text-align: center;
  background: #f5f5f5;
  font-size: 13px;
  color: #999;
}

/* 반응형 */
@media (max-width: 768px) {
  .hero {
    padding: 48px 20px 40px;
    min-height: auto;
  }
  .hero-logo { width: 140px; }
  .hero h1 { font-size: 26px; }
  .hero-desc { font-size: 15px; }
  .hero-buttons { flex-direction: column; }
  .hero-btn { width: 100%; }
  .features { padding: 48px 20px; }
  .features h2, .how-it-works h2, .cta h2 { font-size: 22px; }
  .feature-grid { grid-template-columns: 1fr; gap: 16px; }
  .steps { flex-direction: column; }
  .step-arrow { transform: rotate(90deg); }
  .how-it-works { padding: 48px 20px; }
  .cta { padding: 48px 20px; }
}
</style>
