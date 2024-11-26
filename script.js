// List of topics
const topics = ["Health", "Environment", "Technology", "Economy", "Entertainment", "Sports", "Politics", "Education", "Food", "Travel"];
const topicsContainer = document.getElementById("topics-container");
let topicSelected = false;  // Track if a topic has been selected

// Generate buttons dynamically for each topic
topics.forEach((topic) => {
    const button = document.createElement("button");
    button.className = "bg-gray-700 text-left p-2 rounded hover:bg-gray-600";
    button.setAttribute("data-topic", topic);
    button.innerText = topic;

    // Add event listener to handle topic selection
    button.addEventListener("click", () => selectTopic(topic));

    // Append the button to the container
    topicsContainer.appendChild(button);
});

// Function to handle topic selection
async function selectTopic(topic) {
    // Send the selected topic to the server
    try {
        const response = await fetch("/api/select_topic", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ "topic": topic })
        });
        const data = await response.json();

        // Display server response or fallback message in chat window
        addMessage(data.message || `Let's talk about ${topic}. What would you like to know?`, false);

        // Set topic selected state to enable query mode
        topicSelected = true;
    } catch (error) {
        console.error("Error selecting topic:", error);
        addMessage(`Error selecting topic: ${topic}`, false);
    }
}

// Function to send user messages
async function sendMessage() {
    const userInput = document.getElementById("userInput");
    const userMessage = userInput.value.trim();
    if (!userMessage) return;

    // Display the user message in the chat window
    addMessage(userMessage, true);
    userInput.value = "";  // Clear input field

    try {
        // Determine if chit-chat or query mode based on topic selection
        const endpoint = topicSelected ? "/api/retrieve_and_summarize" : "/api/chat";
        const bodyData = topicSelected ? { "query": userMessage } : { "user_message": userMessage };

        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bodyData)
        });
        const data = await response.json();

        // Display the bot's response in the chat window
        addMessage(data.response || data.summary, false);
    } catch (error) {
        console.error("Error sending message:", error);
        addMessage("Error processing your message. Please try again.", false);
    }
}

// Function to listen for Enter key to send message
function checkEnter(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
}

// Function to add messages to the chat window
function addMessage(text, isUser) {
    const chatOutput = document.getElementById("chatOutput");
    if (!chatOutput) {
        console.error("chatOutput element not found");
        return;
    }
    const message = document.createElement("div");
    message.className = isUser ? "bg-blue-600 text-white p-2 rounded my-2 text-right" : "bg-gray-600 text-white p-2 rounded my-2 text-left";
    message.innerText = text;
    chatOutput.appendChild(message);
    chatOutput.scrollTop = chatOutput.scrollHeight;  // Auto-scroll to the bottom
}

// Attach event listener to the input field for Enter key press
document.getElementById("userInput").addEventListener("keypress", checkEnter);
