/**
 * ResumeLens — Frontend Interactions
 * Drag-and-drop, animated counters, scroll reveals, gauge animation
 */

document.addEventListener('DOMContentLoaded', () => {
    initNavbarScroll();
    initDragAndDrop();
    initScrollAnimations();
    initToastDismiss();
    initGauge();
    initAnimatedCounters();
    initAllBars();
});


/* ═══════════════════════════════════════════════════════════════════════════
   NAVBAR SCROLL EFFECT
   ═══════════════════════════════════════════════════════════════════════════ */
function initNavbarScroll() {
    const navbar = document.getElementById('navbar');
    if (!navbar) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.style.background = 'rgba(6, 10, 20, 0.95)';
            navbar.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.4)';
        } else {
            navbar.style.background = 'rgba(6, 10, 20, 0.8)';
            navbar.style.boxShadow = 'none';
        }
    }, { passive: true });
}


/* ═══════════════════════════════════════════════════════════════════════════
   DRAG & DROP UPLOAD
   ═══════════════════════════════════════════════════════════════════════════ */
function initDragAndDrop() {
    const zone = document.getElementById('upload-zone');
    const input = document.getElementById('resume-input');
    const form = document.getElementById('upload-form');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const removeBtn = document.getElementById('file-remove');
    const submitBtn = document.getElementById('submit-btn');

    if (!zone || !input) return;

    const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
    ];
    const maxSize = 5 * 1024 * 1024; // 5MB

    // Click to browse
    zone.addEventListener('click', (e) => {
        if (e.target === removeBtn || removeBtn?.contains(e.target)) return;
        input.click();
    });

    // Drag events
    ['dragenter', 'dragover'].forEach(evt => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.remove('drag-over');
        });
    });

    zone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    input.addEventListener('change', () => {
        if (input.files.length > 0) {
            handleFile(input.files[0]);
        }
    });

    function handleFile(file) {
        // Validate type
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['pdf', 'docx', 'doc'].includes(ext)) {
            showToast('Please upload a PDF or DOCX file.', 'error');
            return;
        }

        // Validate size
        if (file.size > maxSize) {
            showToast('File size exceeds 5MB limit.', 'error');
            return;
        }

        // Set input files via DataTransfer
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;

        // Show file info
        if (fileInfo && fileName && fileSize) {
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileInfo.classList.remove('hidden');
            fileInfo.classList.add('flex');
        }

        if (submitBtn) submitBtn.disabled = false;
    }

    // Remove file
    if (removeBtn) {
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            input.value = '';
            if (fileInfo) { fileInfo.classList.add('hidden'); fileInfo.classList.remove('flex'); }
            if (submitBtn) submitBtn.disabled = true;
        });
    }

    // Form submit — show loading state
    if (form) {
        form.addEventListener('submit', () => {
            if (submitBtn) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
            }
        });
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showToast(message, type = 'info') {
    let container = document.querySelector('.messages-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'fixed top-[88px] right-6 z-[10000] flex flex-col gap-2 max-w-[400px]';
        document.body.appendChild(container);
    }

    const typeClasses = {
        error: 'bg-[rgba(239,68,68,0.15)] border border-[rgba(239,68,68,0.3)] text-red-300',
        success: 'bg-[rgba(34,197,94,0.15)] border border-[rgba(34,197,94,0.3)] text-green-300',
        info: 'bg-[rgba(59,130,246,0.15)] border border-[rgba(59,130,246,0.3)] text-blue-300',
    };

    const toast = document.createElement('div');
    toast.className = `flex items-center gap-3 py-3.5 px-5 rounded-xl backdrop-blur-[20px] text-sm font-medium ${typeClasses[type] || typeClasses.info}`;
    toast.style.animation = 'slideIn 0.4s ease-out';
    toast.innerHTML = `
        <span>${message}</span>
        <button class="bg-transparent border-none text-inherit cursor-pointer opacity-60 text-lg px-1 hover:opacity-100" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(toast);

    setTimeout(() => toast.remove(), 5000);
}


/* ═══════════════════════════════════════════════════════════════════════════
   SCROLL REVEAL ANIMATIONS
   ═══════════════════════════════════════════════════════════════════════════ */
function initScrollAnimations() {
    const elements = document.querySelectorAll('.animate-on-scroll');
    if (!elements.length) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -40px 0px',
    });

    elements.forEach(el => observer.observe(el));
}


/* ═══════════════════════════════════════════════════════════════════════════
   TOAST DISMISS
   ═══════════════════════════════════════════════════════════════════════════ */
function initToastDismiss() {
    document.querySelectorAll('.toast').forEach(toast => {
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(40px)';
            setTimeout(() => toast.remove(), 400);
        }, 5000);
    });
}


/* ═══════════════════════════════════════════════════════════════════════════
   ATS GAUGE ANIMATION
   ═══════════════════════════════════════════════════════════════════════════ */
function initGauge() {
    const gaugeFill = document.querySelector('.gauge-fill');
    const gaugeScoreEl = document.querySelector('.gauge-score');

    if (!gaugeFill || !gaugeScoreEl) return;

    const score = parseInt(gaugeScoreEl.dataset.score || '0');
    const circumference = 2 * Math.PI * 80; // radius = 80
    const offset = circumference - (score / 100) * circumference;

    // Start with no fill
    gaugeFill.style.strokeDasharray = circumference;
    gaugeFill.style.strokeDashoffset = circumference;

    // Animate after short delay
    requestAnimationFrame(() => {
        setTimeout(() => {
            gaugeFill.style.strokeDashoffset = offset;
        }, 300);
    });

    // Animated counter
    animateCounter(gaugeScoreEl, 0, score, 1800);
}


/* ═══════════════════════════════════════════════════════════════════════════
   ANIMATED COUNTERS
   ═══════════════════════════════════════════════════════════════════════════ */
function animateCounter(element, start, end, duration) {
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + (end - start) * eased);

        element.textContent = current;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

function initAnimatedCounters() {
    const counters = document.querySelectorAll('[data-count]');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const target = parseInt(el.dataset.count || '0');
                animateCounter(el, 0, target, 1500);
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.3 });

    counters.forEach(el => observer.observe(el));
}


/* ═══════════════════════════════════════════════════════════════════════════
   BREAKDOWN BARS & JOB BARS — ANIMATE ON SCROLL
   ═══════════════════════════════════════════════════════════════════════════ */
function initAllBars() {
    const bars = document.querySelectorAll('[data-width]');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const width = el.dataset.width || '0%';
                el.style.width = width;
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.2 });

    bars.forEach(el => {
        el.style.width = '0%';
        observer.observe(el);
    });
}
