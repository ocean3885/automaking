// Audio List JavaScript Module

document.addEventListener('DOMContentLoaded', function() {
    // 전역 변수
    let userCollections = [];
    let selectedAudioId = null;
    let selectedAudioTitle = '';

    // DOM 요소 참조
    const categoryFilter = document.getElementById('categoryFilter');
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('searchInput');
    const addToCollectionBtn = document.getElementById('addToCollectionBtn');

    // 이벤트 리스너 등록
    initEventListeners();

    /**
     * 모든 이벤트 리스너를 초기화합니다.
     */
    function initEventListeners() {
        // 카테고리 필터 변경
        if (categoryFilter) {
            categoryFilter.addEventListener('change', updateUrl);
        }

        // 검색 버튼 클릭
        if (searchBtn) {
            searchBtn.addEventListener('click', updateUrl);
        }

        // 검색 입력 엔터키
        if (searchInput) {
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    updateUrl();
                }
            });
        }

        // 삭제 버튼들
        initDeleteButtons();

        // 보관함 추가 버튼들
        initAddToCollectionButtons();

        // 보관함 추가 확인 버튼
        if (addToCollectionBtn) {
            addToCollectionBtn.addEventListener('click', handleAddToCollection);
        }
    }

    /**
     * URL을 업데이트하여 필터링 및 검색을 적용합니다.
     */
    function updateUrl() {
        const category = categoryFilter ? categoryFilter.value : '';
        const search = searchInput ? searchInput.value : '';
        const params = new URLSearchParams(window.location.search);
        
        if (category) {
            params.set('category', category);
        } else {
            params.delete('category');
        }
        
        if (search) {
            params.set('q', search);
        } else {
            params.delete('q');
        }
        
        params.set('page', '1');
        
        window.location.href = `${window.location.pathname}?${params.toString()}`;
    }

    /**
     * 삭제 버튼들의 이벤트 리스너를 초기화합니다.
     */
    function initDeleteButtons() {
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async function() {
                if (confirm('정말 삭제하시겠습니까?')) {
                    const audioId = this.dataset.id;
                    await deleteAudio(audioId);
                }
            });
        });
    }

    /**
     * 오디오를 삭제합니다.
     * @param {string} audioId - 삭제할 오디오 ID
     */
    async function deleteAudio(audioId) {
        try {
            const csrfToken = getCSRFToken();
            if (!csrfToken) {
                alert('CSRF 토큰을 찾을 수 없습니다. 페이지를 새로고침해주세요.');
                return;
            }

            const response = await fetch(`/audio/${audioId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            
            if (response.ok) {
                window.location.reload();
            } else {
                alert('삭제에 실패했습니다.');
            }
        } catch (error) {
            alert('오류가 발생했습니다.');
            console.error('Delete error:', error);
        }
    }

    /**
     * 보관함 추가 버튼들의 이벤트 리스너를 초기화합니다.
     */
    function initAddToCollectionButtons() {
        document.querySelectorAll('.add-to-collection-btn').forEach(btn => {
            btn.addEventListener('click', async function() {
                selectedAudioId = this.getAttribute('data-audio-id');
                selectedAudioTitle = this.getAttribute('data-audio-title');
                
                await loadUserCollections();
                
                const modal = new bootstrap.Modal(document.getElementById('addToCollectionModal'));
                modal.show();
            });
        });
    }

    /**
     * 사용자의 보관함 목록을 로드합니다.
     */
    async function loadUserCollections() {
        try {
            // Django URL을 전역 변수에서 가져옵니다.
            const getUserCollectionsUrl = window.AUDIO_LIST_CONFIG?.GET_USER_COLLECTIONS_URL || '/collections/list-json/';
            
            const response = await fetch(getUserCollectionsUrl);
            const data = await response.json();
            userCollections = data.collections;
            
            updateCollectionSelect();
        } catch (error) {
            console.error('보관함 로딩 오류:', error);
            alert('보관함을 불러오는 중 오류가 발생했습니다.');
        }
    }

    /**
     * 보관함 선택 드롭다운을 업데이트합니다.
     */
    function updateCollectionSelect() {
        const select = document.getElementById('collectionSelect');
        if (!select) return;

        select.innerHTML = '<option value="">보관함 선택</option>';
        
        userCollections.forEach(collection => {
            const option = document.createElement('option');
            option.value = collection.id;
            option.textContent = `${collection.name} (${collection.count}개)`;
            select.appendChild(option);
        });
        
        if (userCollections.length === 0) {
            select.innerHTML = '<option value="">보관함이 없습니다</option>';
        }
    }

    /**
     * 보관함에 오디오를 추가합니다.
     */
    async function handleAddToCollection() {
        const collectionId = document.getElementById('collectionSelect')?.value;
        
        if (!collectionId) {
            alert('보관함을 선택해주세요.');
            return;
        }

        const csrfToken = getCSRFToken();
        if (!csrfToken) {
            alert('CSRF 토큰을 찾을 수 없습니다. 페이지를 새로고침해주세요.');
            return;
        }

        console.log('Adding audio', selectedAudioId, 'to collection', collectionId);

        try {
            const addToCollectionUrl = `/audio/${selectedAudioId}/add-to-collection/`;
            
            const response = await fetch(addToCollectionUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ collection_id: collectionId })
            });

            const data = await response.json();
            
            console.log('Response:', response.status, data);
            
            if (response.ok) {
                alert(data.message);
                const modal = bootstrap.Modal.getInstance(document.getElementById('addToCollectionModal'));
                if (modal) {
                    modal.hide();
                }
                // 페이지 새로고침하여 버튼 상태 업데이트
                window.location.reload();
            } else {
                alert(data.error || '보관함에 추가하지 못했습니다.');
            }
        } catch (error) {
            alert('오류가 발생했습니다: ' + error.message);
            console.error('Add to collection error:', error);
        }
    }

    /**
     * CSRF 토큰을 가져옵니다.
     * @returns {string|null} CSRF 토큰 또는 null
     */
    function getCSRFToken() {
        // 전역 설정에서 먼저 시도
        if (window.AUDIO_LIST_CONFIG?.CSRF_TOKEN) {
            return window.AUDIO_LIST_CONFIG.CSRF_TOKEN;
        }
        
        // DOM에서 찾기
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfInput ? csrfInput.value : null;
    }
});