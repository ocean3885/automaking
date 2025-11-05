// tailwind.config.js

module.exports = {
  // 🚨 이 부분이 Tailwind가 클래스를 스캔할 경로입니다.
  // 프로젝트 루트를 기준으로 경로를 설정해야 합니다.
  content: [
    '../templates/**/*.html', // 프로젝트 루트의 templates 폴더
    '../../**/*.html', // Tailwind 앱이 프로젝트의 하위 디렉토리인 경우
    '../../**/*.js',
    '../../**/*.py',
    // Django 프로젝트 구조에 맞게 경로를 조정하세요.
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};