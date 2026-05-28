import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-analytics.js";
import { getAuth, signInWithPopup, GoogleAuthProvider, signOut, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

// Your web app's Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyBSiYOh2_dprx2Lvm2SczILpDxlmi-T2q4",
    authDomain: "resumelens-2c217.firebaseapp.com",
    projectId: "resumelens-2c217",
    storageBucket: "resumelens-2c217.firebasestorage.app",
    messagingSenderId: "309996052687",
    appId: "1:309996052687:web:f74d227258c370f4b497ba",
    measurementId: "G-95E2MJ0SDG"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// Helper to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Listen for auth state changes
onAuthStateChanged(auth, async (user) => {
    const authContainer = document.getElementById('auth-container');
    if (!authContainer) return;
    
    if (user) {
        // User is signed in.
        const idToken = await user.getIdToken();
        const csrfToken = getCookie('csrftoken');
        
        // Send token to Django backend
        try {
            const response = await fetch('/api/auth/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ idToken })
            });
            const data = await response.json();
            if (data.success) {
                console.log("Django backend authenticated successfully");
            } else {
                console.error("Django auth failed:", data.error);
            }
        } catch (error) {
            console.error("Backend auth error", error);
        }

        authContainer.innerHTML = `
            <div class="flex items-center gap-3">
                <img src="${user.photoURL}" alt="User Avatar" class="w-8 h-8 rounded-full border border-[--color-border-subtle]">
                <button id="logout-btn" class="bg-[rgba(239,68,68,0.1)] text-red-400 border border-[rgba(239,68,68,0.3)] no-underline text-sm font-medium py-2 px-4 rounded-lg transition-all duration-200 hover:bg-red-500 hover:text-white">Logout</button>
            </div>
        `;
        document.getElementById('logout-btn').addEventListener('click', async () => {
            const csrfToken = getCookie('csrftoken');
            try {
                await fetch('/api/auth/logout/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    }
                });
            } catch (error) {
                console.error("Backend logout error", error);
            }
            signOut(auth).then(() => {
                console.log("Signed out successfully");
            }).catch((error) => {
                console.error("Sign out error", error);
            });
        });
    } else {
        // No user is signed in.
        authContainer.innerHTML = `
            <button id="login-btn" class="bg-[rgba(108,99,255,0.1)] text-[#6c63ff] border border-[#6c63ff] no-underline text-sm font-medium py-2 px-4 rounded-lg transition-all duration-200 hover:bg-[#6c63ff] hover:text-white flex items-center gap-2">
                <svg viewBox="0 0 48 48" width="18px" height="18px"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/><path fill="none" d="M0 0h48v48H0z"/></svg>
                Sign In
            </button>
        `;
        document.getElementById('login-btn').addEventListener('click', () => {
            signInWithPopup(auth, provider).then((result) => {
                console.log("Signed in as", result.user.displayName);
            }).catch((error) => {
                console.error("Sign in error", error);
            });
        });
    }
});