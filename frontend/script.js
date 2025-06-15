document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');

    const imageUpload = document.getElementById('imageUpload');
    const imageFileNameDisplay = document.getElementById('imageFileName');
    const clearImageButton = document.getElementById('clearImageButton');

    const audioUpload = document.getElementById('audioUpload');
    const audioFileNameDisplay = document.getElementById('audioFileName');
    const clearAudioButton = document.getElementById('clearAudioButton');

    let currentSessionState = {};
    let userId = 'user_' + Date.now(); // Simple unique user ID for POC

    let currentImageBase64 = null;
    let currentImageMimeType = null;
    let currentAudioBase64 = null;
    let currentAudioMimeType = null;

    function appendMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');
        
        const p = document.createElement('p');
        p.textContent = text;
        messageDiv.appendChild(p);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to bottom
    }

    // Function to convert file to Base64
    function fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result); // result includes "data:mime/type;base64," prefix
            reader.onerror = error => reject(error);
        });
    }

    async function sendMessage() {
        const messageText = userInput.value.trim();
        if (messageText === '' && !currentImageBase64 && !currentAudioBase64) {
            // Do not send if there's no text and no attachments
            return;
        }

        appendMessage(messageText || "[Sent with attachment]", 'user'); // Show something if only attachment
        userInput.value = '';
        
        // Disable inputs during send
        userInput.disabled = true;
        sendButton.disabled = true;
        imageUpload.disabled = true;
        audioUpload.disabled = true;

        const payload = {
            user_id: userId,
            message: messageText,
            session_state: currentSessionState
        };

        if (currentImageBase64 && currentImageMimeType) {
            payload.image_base64 = currentImageBase64.split(',')[1]; // Remove "data:mime/type;base64," prefix
            payload.image_mime_type = currentImageMimeType;
        }
        if (currentAudioBase64 && currentAudioMimeType) {
            payload.audio_base64 = currentAudioBase64.split(',')[1]; // Remove "data:mime/type;base64," prefix
            payload.audio_mime_type = currentAudioMimeType;
        }

        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Unknown error occurred" }));
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.detail || "Failed to get response"}`);
            }

            const data = await response.json();
            appendMessage(data.bot_response, 'bot');
            currentSessionState = data.session_state || {};

        } catch (error) {
            console.error('Error sending message:', error);
            appendMessage(`Error: Could not connect to the chatbot. ${error.message}`, 'bot');
        } finally {
            // Re-enable inputs
            userInput.disabled = false;
            sendButton.disabled = false;
            imageUpload.disabled = false;
            audioUpload.disabled = false;
            userInput.focus();

            // Clear attachments after sending
            clearImageAttachment();
            clearAudioAttachment();
        }
    }

    // Event listeners for file inputs
    imageUpload.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (file) {
            currentImageMimeType = file.type;
            currentImageBase64 = await fileToBase64(file);
            imageFileNameDisplay.textContent = file.name;
            clearImageButton.style.display = 'inline';
        } else {
            clearImageAttachment();
        }
    });

    audioUpload.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (file) {
            currentAudioMimeType = file.type;
            currentAudioBase64 = await fileToBase64(file);
            audioFileNameDisplay.textContent = file.name;
            clearAudioButton.style.display = 'inline';
        } else {
            clearAudioAttachment();
        }
    });

    // Clear button listeners
    function clearImageAttachment() {
        currentImageBase64 = null;
        currentImageMimeType = null;
        imageUpload.value = ''; // Reset file input
        imageFileNameDisplay.textContent = '';
        clearImageButton.style.display = 'none';
    }

    function clearAudioAttachment() {
        currentAudioBase64 = null;
        currentAudioMimeType = null;
        audioUpload.value = ''; // Reset file input
        audioFileNameDisplay.textContent = '';
        clearAudioButton.style.display = 'none';
    }

    clearImageButton.addEventListener('click', clearImageAttachment);
    clearAudioButton.addEventListener('click', clearAudioAttachment);

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    userInput.focus();
});
