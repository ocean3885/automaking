
// --- 1. 전역 상태 및 유틸리티 함수 정의  ---
let _fadeInterval = null;
let isEditingTitle = false;
let _currentActiveIndex = -1;
let isRepeating = false;
let currentRepeatStart = 0;
let currentRepeatEnd = 0;

// 시간을 mm:ss 형식으로 포맷팅
function formatTime(seconds) {
    seconds = Math.floor(seconds);
    const minutes = Math.floor(seconds / 60);
    seconds = seconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function fadeVolume(audio, target, duration = 150, cb) {
    if (_fadeInterval) clearInterval(_fadeInterval);
    const start = Number.isFinite(audio.volume) ? audio.volume : 1;
    const diff = target - start;
    const steps = Math.max(1, Math.floor(duration / 16));
    let i = 0;
    const stepTime = duration / steps;
    _fadeInterval = setInterval(() => {
        i++;
        const v = start + diff * (i / steps);
        audio.volume = Math.max(0, Math.min(1, v));
        if (i >= steps) {
            clearInterval(_fadeInterval);
            _fadeInterval = null;
            if (cb) cb();
        }
    }, stepTime);
}

function seekWithFade(audio, timeSec, updateActiveSentenceByTime) {
    const doSeekAndPlay = () => {
        try {
            audio.currentTime = timeSec;
            const onSeeked = () => {
                audio.removeEventListener('seeked', onSeeked);
                audio.play().catch(err => console.warn('play error:', err));
                fadeVolume(audio, 1, 160);
                updateActiveSentenceByTime(timeSec);
            };
            audio.addEventListener('seeked', onSeeked);
        } catch (e) {
            console.warn('seek error', e);
            audio.play().catch(() => { });
            fadeVolume(audio, 1, 160);
        }
    };

    fadeVolume(audio, 0, 120, () => {
        if (audio.readyState >= 1) {
            doSeekAndPlay();
        } else {
            audio.load();
            const onLoadedMetadata = () => {
                audio.removeEventListener('loadedmetadata', onLoadedMetadata);
                doSeekAndPlay();
            };
            audio.addEventListener('loadedmetadata', onLoadedMetadata);
        }
    });
}

function updateActiveSentenceByTime(time) {
    const sentenceItems = Array.from(document.querySelectorAll('.sentence-item'));
    let foundActive = false;
    let newActiveIndex = -1;

    sentenceItems.forEach((item, idx) => {
        const start = parseFloat(item.getAttribute('data-start')) || 0;
        const end = parseFloat(item.getAttribute('data-end')) || 0;
        const isActive = (time >= start && time < end);

        if (isActive) {
            foundActive = true;
            newActiveIndex = idx;
            if (_currentActiveIndex !== idx) {
                _currentActiveIndex = idx;
            }
        }
    });

    if (!foundActive && _currentActiveIndex !== -1) {
        newActiveIndex = _currentActiveIndex;
    }

    sentenceItems.forEach((item, idx) => {
        if (idx === newActiveIndex) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    if (isRepeating && foundActive && (_currentActiveIndex !== newActiveIndex)) {
        isRepeating = false;
        document.getElementById('repeatBtn')?.classList.remove('active');
    }
}


document.addEventListener('DOMContentLoaded', function () {

    const CONFIG = window.AUDIO_DETAIL_CONFIG;

    // --- 요소 변수 선언 ---
    const audio = document.getElementById('audio-player');
    const titleDisplay = document.getElementById('titleDisplay');
    const editTitleBtn = document.getElementById('editTitleBtn');
    const categorySelect = document.getElementById('categorySelect');
    const deleteBtn = document.getElementById('deleteBtn');
    const repeatBtn = document.getElementById('repeatBtn');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const stopBtn = document.getElementById('stopBtn');
    const progressBar = document.getElementById('progressBar');
    const currentTimeEl = document.getElementById('currentTime');
    const durationEl = document.getElementById('duration');
    const speedOptions = document.querySelectorAll('.speed-option');
    const speedLabel = document.getElementById('speedLabel');
    const sentenceItems = Array.from(document.querySelectorAll('.sentence-item'));


    // --- [오디오 플레이어 로직] ---
    // (재생/정지, 속도, 반복, 키보드 조작 이벤트 리스너들을 여기에 유지)

    // (playPromiseHandler, playPauseBtn.addEventListener, audio.addEventListener, speedOptions.forEach, repeatBtn.addEventListener 등)
    const playPromiseHandler = (error) => {
        // AbortError는 사용자의 빠른 조작으로 발생할 수 있으므로 무시합니다.
        if (error.name !== 'AbortError') {
            console.error('오디오 재생 실패:', error);
        }
    };

    // 1. 재생/일시정지 버튼 클릭
    playPauseBtn.addEventListener('click', () => {
        if (audio.paused) {
            audio.play().catch(playPromiseHandler);
        } else {
            audio.pause();
        }
    });

    // 2. 정지 버튼 클릭
    stopBtn.addEventListener('click', () => {
        audio.pause();
        audio.currentTime = 0;
        playPauseBtn.innerHTML = '<i class="fas fa-play"></i>'; // 아이콘을 재생 상태로 복원
    });

    // 3. 오디오 상태 변경 이벤트
    audio.addEventListener('play', () => {
        playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>'; // 아이콘 변경
    });
    audio.addEventListener('pause', () => {
        playPauseBtn.innerHTML = '<i class="fas fa-play"></i>'; // 아이콘 변경
    });

    // 4. 재생 시간 및 프로그레스 바 업데이트
    audio.addEventListener('loadedmetadata', () => {
        durationEl.textContent = formatTime(audio.duration); // 총 길이 표시
    });

    audio.addEventListener('timeupdate', () => {
        const percent = (audio.currentTime / audio.duration) * 100;
        progressBar.style.width = `${percent}%`;
        currentTimeEl.textContent = formatTime(audio.currentTime);

        // 반복 재생 로직 (반복 시작/끝 지점 체크)
        if (isRepeating && audio.currentTime >= currentRepeatEnd) {
            audio.currentTime = currentRepeatStart;
        }

        // 문장 하이라이트 및 반복 버튼 활성화/비활성화
        updateActiveSentenceByTime(audio.currentTime);
        repeatBtn.disabled = !document.querySelector('.sentence-item.active');
    });

    // 5. 재생 속도 변경
    speedOptions.forEach(option => {
        option.addEventListener('click', (e) => {
            e.preventDefault();
            const speed = parseFloat(option.getAttribute('data-speed'));
            audio.playbackRate = speed;
            speedLabel.textContent = `${speed}x`;

            // 활성 상태 업데이트
            speedOptions.forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');
        });
    });

    // 6. 반복 재생 버튼 클릭 이벤트
    repeatBtn.addEventListener('click', () => {
        isRepeating = !isRepeating;
        repeatBtn.classList.toggle('active');

        if (isRepeating) {
            const activeItem = document.querySelector('.sentence-item.active');
            if (activeItem) {
                currentRepeatStart = parseFloat(activeItem.getAttribute('data-start')) || 0;
                currentRepeatEnd = parseFloat(activeItem.getAttribute('data-end')) || 0;

                // 즉시 반복 시작 지점으로 이동하여 재생
                audio.currentTime = currentRepeatStart;
                audio.play().catch(playPromiseHandler);
            } else {
                // 활성 문장이 없으면 비활성화
                isRepeating = false;
                repeatBtn.classList.remove('active');
                alert("반복할 문장을 먼저 클릭하여 활성화해 주세요.");
            }
        }
    });

    // 7. 키보드 좌/우 화살표로 -10초/+10초 이동
    document.addEventListener('keydown', (e) => {
        const tag = e.target && e.target.tagName;
        // 텍스트 입력 중일 경우 키 조작 방지
        if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable) return;

        const isLeft = e.key === 'ArrowLeft' || e.key === 'Left' || e.keyCode === 37;
        const isRight = e.key === 'ArrowRight' || e.key === 'Right' || e.keyCode === 39;
        if (!isLeft && !isRight) return;

        e.preventDefault();
        const cur = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;

        if (isLeft) {
            const newTime = Math.max(0, cur - 10);
            audio.currentTime = newTime;
            audio.play().catch(playPromiseHandler);
        } else if (isRight) {
            let newTime = cur + 10;
            if (Number.isFinite(audio.duration)) {
                newTime = Math.min(audio.duration, newTime);
            }
            audio.currentTime = newTime;
            audio.play().catch(playPromiseHandler);
        }
    });

    // 8. 문장 클릭 시 해당 시간으로 이동 
    sentenceItems.forEach(item => {
        item.addEventListener('click', () => {
            const start = parseFloat(item.getAttribute('data-start')) || 0;
            item.scrollIntoView({ behavior: 'smooth', block: 'center' });
            seekWithFade(audio, start, updateActiveSentenceByTime);
        });
    });


    // --- [보관함에 추가 기능] ---
    let userCollections = [];

    async function loadUserCollections() {
        try {
            // 🚨 템플릿 태그 대신 CONFIG.GET_COLLECTIONS_URL 사용
            const response = await fetch(CONFIG.GET_COLLECTIONS_URL);

            // --- [데이터 처리 및 드롭다운 메뉴 채우기] ---
            const data = await response.json();
            userCollections = data.collections;
            const select = document.getElementById('collectionSelect');

            // 드롭다운 초기화
            select.innerHTML = '<option value="">보관함 선택</option>';

            // 보관함 목록을 반복하여 <option> 요소 추가
            userCollections.forEach(collection => {
                const option = document.createElement('option');
                option.value = collection.id;
                // 보관함 이름과 (개수)를 함께 표시
                option.textContent = `${collection.name} (${collection.count}개)`;
                select.appendChild(option);
            });

            if (userCollections.length === 0) {
                select.innerHTML = '<option value="">보관함이 없습니다</option>';
            }

        } catch (error) {
            console.error('보관함 로딩 오류:', error);
            // 로딩 실패 시 드롭다운 상태를 업데이트
            document.getElementById('collectionSelect').innerHTML = '<option value="">목록 로딩 실패</option>';
        }
    }

    const addToCollectionModal = document.getElementById('addToCollectionModal');
    if (addToCollectionModal) { addToCollectionModal.addEventListener('show.bs.modal', loadUserCollections); }

    document.getElementById('addToCollectionBtn')?.addEventListener('click', async function () {
        const collectionId = document.getElementById('collectionSelect').value;
        if (!collectionId) { alert('보관함을 선택해주세요.'); return; }

        try {
            // 🚨 템플릿 태그 대신 CONFIG.ADD_TO_COLLECTION_URL 사용
            const response = await fetch(CONFIG.ADD_TO_COLLECTION_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CONFIG.CSRF_TOKEN },
                body: JSON.stringify({ collection_id: collectionId })
            });

            const data = await response.json();
            if (response.ok) {
                alert(data.message);
                const modal = bootstrap.Modal.getInstance(addToCollectionModal);
                if (modal) modal.hide();
                location.reload();
            } else {
                alert(data.error || '보관함에 추가하지 못했습니다.');
            }
        } catch (error) {
            alert('보관함 추가 중 네트워크 오류가 발생했습니다: ' + error.message);
            console.error('Error:', error);
        }
    });
});