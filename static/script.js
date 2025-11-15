// List of topics
const topics = ["Health", "Environment", "Technology", "Economy", "Entertainment", "Sports", "Politics", "Education", "Food", "Travel"];
let topicSelected = false;  // Track if a topic has been selected
let selectedTopicButton = null;  // Track the currently selected topic button
let currentSelectedTopic = null;  // Track the currently selected topic name

let responseTimes = [];
let docsRetrieved = [];
let topicFrequency = {};

// Function to handle topic selection
async function selectTopic(topic) {
    try {
        // If clicking the same topic, deselect it
        if (currentSelectedTopic === topic && topicSelected) {
            // Deselect topic
            const response = await fetch("/api/deselect_topic", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });
            const data = await response.json();
            
            // Remove blue highlighting
            if (selectedTopicButton) {
                selectedTopicButton.classList.remove("bg-blue-600", "ring-2", "ring-blue-400");
                selectedTopicButton.classList.add("bg-gray-700");
                selectedTopicButton = null;
            }
            
            currentSelectedTopic = null;
            topicSelected = false;
            addMessage(data.message || "Returned to chit-chat mode. Feel free to chat about anything!", false);
            return;
        }
        
        // Remove blue highlighting from previously selected button
        if (selectedTopicButton) {
            selectedTopicButton.classList.remove("bg-blue-600", "ring-2", "ring-blue-400");
            selectedTopicButton.classList.add("bg-gray-700");
        }
        
        const response = await fetch("/api/select_topic", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ "topic": topic })
        });
        const data = await response.json();

        // Find and highlight the selected button
        const buttons = document.querySelectorAll('[data-topic]');
        buttons.forEach(btn => {
            if (btn.getAttribute("data-topic") === topic) {
                btn.classList.remove("bg-gray-700");
                btn.classList.add("bg-blue-600", "ring-2", "ring-blue-400");
                selectedTopicButton = btn;
            }
        });

        addMessage(data.message || `Let's talk about ${topic}. What would you like to know?`, false);

        // Set topic selected state to enable query mode
        topicSelected = true;
        currentSelectedTopic = topic;
    } catch (error) {
        console.error("Error selecting topic:", error);
        addMessage(`Error selecting topic: ${topic}`, false);
    }
}

// Function to send user messages
async function sendMessage() {
    console.log("sendMessage() called");
    const userInput = document.getElementById("userInput");
    if (!userInput) {
        console.error("userInput element not found");
        return;
    }
    
    const userMessage = userInput.value.trim();
    console.log("User message:", userMessage);
    if (!userMessage) {
        console.log("Empty message, returning");
        return;
    }

    // Display the user message in the chat window
    console.log("Adding user message to chat");
    addMessage(userMessage, true);
    userInput.value = "";  // Clear input field

    // Add a loading message in the chat window and store reference
    const loadingMessageElement = addMessage("...", false, true);  // This will be the "loading" message

    try {
        // Determine if chit-chat or query mode based on topic selection
        const endpoint = topicSelected ? "/api/retrieve_and_summarize" : "/api/chat";
        const bodyData = topicSelected ? { "query": userMessage } : { "user_message": userMessage };
        
        console.log("Mode:", topicSelected ? "Query" : "Chit-Chat", "Endpoint:", endpoint);

        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bodyData)
        });

        // Remove the loading message
        if (loadingMessageElement) {
            loadingMessageElement.remove();
        }

        // Check if response is ok
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}: ${response.statusText}` }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();

        // Update visualizations if in query mode
        if (topicSelected && data.response_time && data.docs_retrieved_count && data.topic) {
            updateResponseTimeChart(data.response_time);
            updateDocsRetrievedChart(data.docs_retrieved_count);
            updateTopicPopularityChart(data.topic);
        }

        // Display the bot's response in the chat window
        addMessage(data.response || data.summary || "No response received", false);
    } catch (error) {
        console.error("Error sending message:", error);
        // Remove loading message on error
        if (loadingMessageElement) {
            loadingMessageElement.remove();
        }
        addMessage(`Error: ${error.message || "Failed to process your message. Please try again."}`, false);
    }
}

// Function to listen for Enter key
function checkEnter(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
}

// Function to add messages to the chat window
function addMessage(text, isUser, isLoading = false) {
    console.log("addMessage called:", text, "isUser:", isUser);
    const chatOutput = document.getElementById("chatOutput");
    if (!chatOutput) {
        console.error("chatOutput element not found in addMessage");
        return null;
    }
    const message = document.createElement("div");
    message.className = isUser ? "bg-blue-600 text-white p-2 rounded my-2 text-right" : "bg-gray-600 text-white p-2 rounded my-2 text-left";
    if (text === "..." || isLoading) {
        message.className += " loading-message";  // Add a class to the loading message
    }
    message.innerText = text;
    chatOutput.appendChild(message);
    chatOutput.scrollTop = chatOutput.scrollHeight;  // Auto-scroll to the bottom
    console.log("Message added to chatOutput, total children:", chatOutput.children.length);
    return message;  // Return the element so it can be removed later
}

// Initialize Charts (will be initialized in DOMContentLoaded)
let responseTimeChart = null;
let docsRetrievedChart = null;
let topicPopularityChart = null;

// Update visualizations dynamically
function updateResponseTimeChart(time) {
    if (!responseTimeChart) return;
    responseTimes.push(time);
    responseTimeChart.data.labels.push(`Query ${responseTimes.length}`);
    responseTimeChart.data.datasets[0].data = responseTimes;
    responseTimeChart.update();
}

function updateDocsRetrievedChart(count) {
    if (!docsRetrievedChart) return;
    docsRetrieved.push(count);
    docsRetrievedChart.data.labels.push(`Query ${docsRetrieved.length}`);
    docsRetrievedChart.data.datasets[0].data = docsRetrieved;
    docsRetrievedChart.update();
}

function updateTopicPopularityChart(topic) {
    if (!topicPopularityChart) return;
    if (!topicFrequency[topic]) topicFrequency[topic] = 0;
    topicFrequency[topic]++;
    topicPopularityChart.data.labels = Object.keys(topicFrequency);
    topicPopularityChart.data.datasets[0].data = Object.values(topicFrequency);
    topicPopularityChart.update();
}

// Check model loading status
async function checkModelStatus() {
    try {
        const response = await fetch("/api/status");
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        
        console.log("Status check:", data); // Debug log
        
        const loadingOverlay = document.getElementById("loadingOverlay");
        const loadingText = document.getElementById("loadingText");
        
        if (!loadingOverlay || !loadingText) {
            console.error("Loading overlay elements not found");
            return;
        }
        
        // Check if models are fully loaded FIRST
        if (data.loaded === true && data.loading === false) {
            // Hide overlay when models are loaded
            console.log("✅ Models loaded successfully! Hiding overlay...");
            loadingOverlay.style.display = "none";
            loadingOverlay.classList.add("hidden");
            loadingOverlay.setAttribute("data-loaded", "true");
            // Stop checking status
            return;
        }
        
        // Otherwise, show overlay if still loading
        if (data.loading === true || data.loaded === false) {
            // Show overlay and update progress
            loadingOverlay.style.display = "flex";
            loadingOverlay.classList.remove("hidden");
            loadingText.textContent = data.progress || "Loading models...";
            // Check again in 500ms
            setTimeout(checkModelStatus, 500);
        } else {
            // Unknown state, keep checking
            console.warn("Unknown loading state:", data);
            setTimeout(checkModelStatus, 1000);
        }
    } catch (error) {
        console.error("Error checking model status:", error);
        // Keep showing overlay and retry after 1 second
        const loadingOverlay = document.getElementById("loadingOverlay");
        const loadingText = document.getElementById("loadingText");
        if (loadingOverlay) {
            loadingOverlay.style.display = "flex";
            loadingOverlay.classList.remove("hidden");
        }
        if (loadingText) {
            loadingText.textContent = "Connecting to server...";
        }
        setTimeout(checkModelStatus, 1000);
    }
}

// Start checking model loading status immediately
// This ensures the overlay is visible as soon as possible
(function() {
    // Ensure overlay is visible
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
        overlay.classList.remove('hidden');
    }
    
    // Start checking status immediately
    checkModelStatus();
})();

// Attach event listeners when DOM is ready
document.addEventListener("DOMContentLoaded", function() {
    // Continue checking model status (in case it wasn't already started)
    if (!window.modelStatusChecked) {
        checkModelStatus();
        window.modelStatusChecked = true;
    }
    
    // Initialize chit-chat mode on startup
    topicSelected = false;
    
    // Show welcome message for chit-chat mode
    addMessage("Hello! I'm an Information Retrieval (IR) Chatbot powered by AI. I can help you in two ways:\n\n💬 Chit-Chat Mode (current): Have a casual conversation with me about anything!\n\n🔍 Query Mode: Select a topic from the sidebar (Health, Technology, Sports, etc.) and ask me specific questions. I'll search through Wikipedia articles, retrieve relevant documents, and provide AI-generated summaries.\n\nTry asking me something, or select a topic to get started!", false);
    
    // Generate buttons dynamically for each topic
    const topicsContainer = document.getElementById("topics-container");
    if (topicsContainer) {
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
    }
    
    const userInput = document.getElementById("userInput");
    const sendButton = document.getElementById("sendButton");
    
    if (userInput) {
        userInput.addEventListener("keypress", checkEnter);
    }
    
    if (sendButton) {
        sendButton.addEventListener("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log("Send button clicked, calling sendMessage()");
            sendMessage();
        });
        console.log("Send button event listener attached");
    } else {
        console.error("sendButton element not found!");
    }
    
    // Verify chatOutput exists
    const chatOutput = document.getElementById("chatOutput");
    if (chatOutput) {
        console.log("chatOutput element found");
    } else {
        console.error("chatOutput element not found!");
    }
    
    // Initialize charts only if elements exist
    const responseTimeChartEl = document.getElementById("responseTimeChart");
    const docsRetrievedChartEl = document.getElementById("docsRetrievedChart");
    const topicPopularityChartEl = document.getElementById("topicPopularityChart");
    
    if (responseTimeChartEl && typeof Chart !== 'undefined') {
        responseTimeChart = new Chart(responseTimeChartEl, {
            type: "line",
            data: {
                labels: [],
                datasets: [{
                    label: "Response Time (s)",
                    data: [],
                    borderColor: "rgb(75, 192, 192)",
                    backgroundColor: "rgba(75, 192, 192, 0.2)",
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
    
    if (docsRetrievedChartEl && typeof Chart !== 'undefined') {
        docsRetrievedChart = new Chart(docsRetrievedChartEl, {
            type: "bar",
            data: {
                labels: [],
                datasets: [{
                    label: "Documents Retrieved",
                    data: [],
                    backgroundColor: "rgb(54, 162, 235)",
                    borderColor: "rgb(54, 162, 235)",
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
    
    if (topicPopularityChartEl && typeof Chart !== 'undefined') {
        topicPopularityChart = new Chart(topicPopularityChartEl, {
            type: "pie",
            data: {
                labels: [],
                datasets: [{
                    label: "Topic Popularity",
                    data: [],
                    backgroundColor: [
                        "rgb(255, 99, 132)",
                        "rgb(54, 162, 235)",
                        "rgb(255, 206, 86)",
                        "rgb(75, 192, 192)",
                        "rgb(153, 102, 255)",
                        "rgb(255, 159, 64)"
                    ]
                }]
            },
            options: { responsive: true }
        });
    }
});

