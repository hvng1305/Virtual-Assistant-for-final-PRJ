// ====== SpeechRecognition & SpeechSynthesis ======
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const synth = window.speechSynthesis;

const btnMic = document.getElementById("btnMic");
const assistantReply = document.getElementById("assistantReply");
const btnSend = document.getElementById("btnSend");
const manualText = document.getElementById("manualText");

let recognition = null;
let listening = false;

// Nói
function speak(text) {
  if (!text) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = "vi-VN";
  utter.rate = 1;
  utter.pitch = 1;
  synth.cancel();
  synth.speak(utter);
}

// Gõ chữ từng ký tự (typewriter effect cho bot trả lời)
async function typeReply(text) {
  assistantReply.textContent = "";
  let i = 0;
  function typing() {
    if (i < text.length) {
      assistantReply.textContent += text.charAt(i);
      i++;
      setTimeout(typing, 30);
    }
  }
  typing();
}

// Gửi đến server
async function askServer(text) {
  const res = await fetch("/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text})
  });
  const data = await res.json();
  return data.reply || "Mình chưa rõ ý bạn.";
}

async function handleText(text) {
  if (!text) return;
  manualText.value = "";
  const reply = await askServer(text);
  await typeReply(reply);
  speak(reply);
}

// ===== Nhận giọng nói =====
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = "vi-VN";
  recognition.interimResults = true;
  recognition.continuous = false;

  let finalTranscript = "";

  recognition.onstart = () => {
    listening = true;
    btnMic.textContent = "🛑";
  };

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += transcript;
      } else {
        interim += transcript;
      }
    }
    manualText.value = finalTranscript || interim;
  };

  recognition.onerror = (e) => {
    listening = false;
    btnMic.textContent = "🎤";
    manualText.value = "Lỗi: " + e.error;
  };

  recognition.onend = async () => {
    btnMic.textContent = "🎤";
    listening = false;
    const text = manualText.value.trim();
    if (text) await handleText(text);
  };

  btnMic.addEventListener("click", () => {
    if (!listening) {
      finalTranscript = "";
      recognition.start();
    } else {
      recognition.stop();
    }
  });
} else {
  btnMic.disabled = true;
  btnMic.textContent = "🚫";
  manualText.value = "Trình duyệt không hỗ trợ microphone";
}

// ===== Gửi nhập tay =====
btnSend.addEventListener("click", async () => {
  const text = manualText.value.trim();
  await handleText(text);
});

// ===== Intro typewriter + chuyển màn hình =====
const intro = document.getElementById("intro");
const introText = document.getElementById("introText");
const chatContainer = document.getElementById("chatContainer");

const textIntro = "Xin chào! Mình là Friday - Trợ lý ảo tiếng Việt.";
let idx = 0;

function typeWriter() {
  if (idx < textIntro.length) {
    introText.textContent += textIntro.charAt(idx);
    idx++;
    setTimeout(typeWriter, 50);
  } else {
    setTimeout(() => {
      intro.classList.add("fade-out");
      setTimeout(() => {
        intro.classList.add("hidden");
        chatContainer.style.opacity = "1";
        chatContainer.classList.add("fade-in");
      }, 1000);
    }, 1500);
  }
}
window.onload = typeWriter;
