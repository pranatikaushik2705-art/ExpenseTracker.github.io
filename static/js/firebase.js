// -----------------------------
// Firebase App & Auth SDK
// -----------------------------
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.11.0/firebase-app.js";
import { 
  getAuth, 
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail
} from "https://www.gstatic.com/firebasejs/10.11.0/firebase-auth.js";

// -----------------------------
// Your Firebase Configuration
// -----------------------------
const firebaseConfig = {
  apiKey: "AIzaSyBNyoY-61dZmQnrhMzpB0HzGrwYC4vIoH4",
  authDomain: "expensetracker-ddf7a.firebaseapp.com",
  projectId: "expensetracker-ddf7a",
  storageBucket: "expensetracker-ddf7a.firebasestorage.app",
  messagingSenderId: "788001622860",
  appId: "1:788001622860:web:c8d2ec931e33b5135a9de9"
};

// -----------------------------
// Initialize Firebase
// -----------------------------
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Export to all HTML pages
export {
  auth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail
};