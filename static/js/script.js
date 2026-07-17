const uploadForm = document.getElementById("uploadForm");
const pdfInput = document.getElementById("pdf");
const fileName = document.getElementById("fileName");
const chatBox = document.getElementById("chatBox");
const uploadButton = uploadForm.querySelector("button");
const askBtn = document.getElementById("askBtn");
const questionInput = document.getElementById("question");
const clearChatBtn = document.getElementById("clearChatBtn");

// ===============================
// Helper Functions
// ===============================

function scrollToBottom() {
    chatBox.scrollTo({
        top: chatBox.scrollHeight,
        behavior: "smooth"
    });
}

function focusQuestionInput() {
    questionInput.focus();
}

// Disable chat until PDF is uploaded
askBtn.disabled = true;
questionInput.disabled = true;

// Upload PDF
uploadForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    if (pdfInput.files.length === 0) {

        document.getElementById("uploadStatus").innerHTML =
            "❌ Please select a PDF first.";

        return;
    }

    const formData = new FormData(uploadForm);

    uploadButton.disabled = true;
    askBtn.disabled = true;
    uploadButton.innerHTML = `
    <span class="spinner"></span>
    Uploading...
`;

    try {

        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        console.log(data);

        if (!response.ok) {

            showToast(`❌ ${data.error}`, "error");

            return;
        }

        showToast("✅ PDF uploaded successfully!");

        const documentInfo = document.getElementById("documentInfo");
        document.getElementById("docName").textContent = data.filename;

        document.getElementById("docSize").textContent = `${data.file_size} KB`;

        document.getElementById("docCharacters").textContent = data.characters;

        document.getElementById("docChunks").textContent = data.chunks;

        document.getElementById("docEmbeddings").textContent = data.embeddings;

        document.getElementById("docUploadTime").textContent = data.uploaded_at;

documentInfo.classList.remove("hidden");

        // Reset chat
        chatBox.innerHTML = `
            <div class="empty-chat">

    <div class="empty-icon">🤖</div>

    <h3>Ready to Chat</h3>

    <p>Upload a PDF and ask questions about its contents.</p>

    <div class="example-prompts">

        <div class="prompt-chip">
            📄 Summarize this document
        </div>

        <div class="prompt-chip">
            🔍 What are the key points?
        </div>

        <div class="prompt-chip">
            👤 Who is the author?
        </div>

        <div class="prompt-chip">
            📊 Give me a short summary
        </div>

    </div>

</div>
        `;

        // Enable chatting
        askBtn.disabled = false;
        questionInput.disabled = false;
        questionInput.value = "";
        focusQuestionInput();

        // Reset upload input
        pdfInput.value = "";
        fileName.textContent = "No file selected";

    }
    catch (error) {

        console.error(error);

        showToast("❌ Upload failed.", "error");

    }
    finally {

        uploadButton.disabled = false;
        uploadButton.innerText = "Upload PDF";

    }

});

// Ask Question
askBtn.addEventListener("click", async () => {

    const question = questionInput.value.trim();

    if (!question) {
        return;
    }

    questionInput.disabled = true;
    askBtn.disabled = true;
    askBtn.innerHTML = "...";

    if (chatBox.querySelector(".empty-chat")) {
        chatBox.innerHTML = "";

        const suggestions = document.querySelector(".suggestion-container");
        if (suggestions) {
            suggestions.style.display = "none";
}
    }

    chatBox.innerHTML += `
        <div class="user-message">
            <strong>You</strong><br>
            ${question}
        </div>

        <div class="bot-message thinking">

    <div class="bot-header">
        <strong>Assistant</strong>
    </div>

    <div class="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
    </div>

</div>
    `;

    scrollToBottom();

    try {

        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error);
        }

        const sourcesHTML = (data.sources || [])
            .map((source, index) => `
                <details class="source-box">
                <summary>
                📄 Source ${index + 1}
                </summary>
                    <p>${source}</p>
                </details>
            `)
            .join("");

        const thinkingMessage = document.querySelector(".thinking");

        thinkingMessage.outerHTML = `
<div class="bot-message">

    <div class="bot-header">
        <strong>Assistant</strong>

        <button class="copy-btn">
            📋 Copy
        </button>

    </div>

    <div class="bot-answer">
    ${marked.parse(data.answer)}
    </div>

    <div class="sources">
        ${sourcesHTML}
    </div>

</div>
`;

// Copy button
        document.querySelectorAll(".copy-btn").forEach(button => {

            button.onclick = async () => {

                const answer = button
                    .closest(".bot-message")
                    .querySelector(".bot-answer")
                    .innerText;

                await navigator.clipboard.writeText(answer);
                showToast("📋 Copied to clipboard!");


            };
        });

        scrollToBottom();
        questionInput.value = "";
        focusQuestionInput();
}
    catch (error){
        console.error(error);
        const thinkingMessage = document.querySelector(".thinking");
        if (thinkingMessage) {
        thinkingMessage.outerHTML = `
        <div class="bot-message">
            <strong>Assistant</strong><br>
            Something went wrong.
        </div>
        `;

    }
}
    finally {

        askBtn.disabled = false;

        questionInput.disabled = false;

        askBtn.innerHTML = "➜";

        focusQuestionInput();

    }
});

// File Name
pdfInput.addEventListener("change", () => {

    if (pdfInput.files.length > 0) {
        fileName.textContent = pdfInput.files[0].name;
    }
    else {
        fileName.textContent = "No file selected";
    }

});

// Drag & Drop
const uploadArea = document.querySelector(".upload-area");
uploadArea.addEventListener("dragover", (event) => {

    event.preventDefault();
    uploadArea.classList.add("dragover");

});

uploadArea.addEventListener("dragleave", () => {

    uploadArea.classList.remove("dragover");

});

uploadArea.addEventListener("drop", (event) => {

    event.preventDefault();

    uploadArea.classList.remove("dragover");

    pdfInput.files = event.dataTransfer.files;

    if (pdfInput.files.length > 0) {
        fileName.textContent = pdfInput.files[0].name;
    }

});

// ===============================
// Enter Key
// ===============================

questionInput.addEventListener("keydown", (event) => {

    if (event.key === "Enter") {

        event.preventDefault();
        askBtn.click();

    }

});

// ===============================
// Clear Chat
// ===============================

clearChatBtn.addEventListener("click", () => {

    document.getElementById("documentInfo")
    .classList.add("hidden");

    chatBox.innerHTML = `
        <div class="empty-chat">

            <div class="empty-icon">🤖</div>

            <h3>Start a conversation</h3>

            <p>
                Upload a PDF and ask anything about its contents.
            </p>

        </div>
    `;

    questionInput.value = "";
    focusQuestionInput();

});

// ===============================
// Prompt Chips
// ===============================

document.addEventListener("click", (event) => {

    const chip = event.target.closest(".prompt-chip");

    if (!chip) return;

    if (askBtn.disabled) return;

    questionInput.value = chip.innerText.trim();

    askBtn.click();

});