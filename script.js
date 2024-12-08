// List of topics
const topics = ["Health", "Environment", "Technology", "Economy", "Entertainment", "Sports", "Politics", "Education", "Food", "Travel"];
const topicsContainer = document.getElementById("topics-container");
let topicSelected = false;  // Track if a topic has been selected

let responseTimes = [];
let docsRetrieved = [];
let topicFrequency = {};

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
    try {
        const response = await fetch("/api/select_topic", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ "topic": topic })
        });
        const data = await response.json();

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

    // Add a loading message in the chat window
    addMessage("...", false);  // This will be the "loading" message

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


        // Remove the loading message and add the actual response
        const chatOutput = document.getElementById("chatOutput");
        if (chatOutput) {
            const loadingMessage = chatOutput.querySelector('.loading-message');
            if (loadingMessage) {
                loadingMessage.remove();  // Remove the "loading" message
            }
        }

        // Update visualizations if in query mode
        if (topicSelected && data.response_time && data.docs_retrieved_count && data.topic) {
            updateResponseTimeChart(data.response_time);
            updateDocsRetrievedChart(data.docs_retrieved_count);
            updateTopicPopularityChart(data.topic);
        }

        // Display the bot's response in the chat window
        addMessage(data.response || data.summary, false);
    } catch (error) {
        console.error("Error sending message:", error);
        addMessage("Error processing your message. Please try again.", false);
    }
}

// Function to listen for Enter key
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
    if (text === "...") {
        message.className += " loading-message";  // Add a class to the loading message
    }
    message.innerText = text;
    chatOutput.appendChild(message);
    chatOutput.scrollTop = chatOutput.scrollHeight;  // Auto-scroll to the bottom
}

// Initialize Charts
const responseTimeChart = new Chart(document.getElementById("responseTimeChart"), {
    type: "line",
    data: {
        labels: [],
        datasets: [{
            label: "Response Time (ms)",
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

const docsRetrievedChart = new Chart(document.getElementById("docsRetrievedChart"), {
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

const topicPopularityChart = new Chart(document.getElementById("topicPopularityChart"), {
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

// Update visualizations dynamically
function updateResponseTimeChart(time) {
    responseTimes.push(time);
    responseTimeChart.data.labels.push(`Query ${responseTimes.length}`);
    responseTimeChart.data.datasets[0].data = responseTimes;
    responseTimeChart.update();

}

function updateDocsRetrievedChart(count) {
    docsRetrieved.push(count);
    docsRetrievedChart.data.labels.push(`Query ${docsRetrieved.length}`);
    docsRetrievedChart.data.datasets[0].data = docsRetrieved;
    docsRetrievedChart.update();
}

function updateTopicPopularityChart(topic) {
    if (!topicFrequency[topic]) topicFrequency[topic] = 0;
    topicFrequency[topic]++;
    topicPopularityChart.data.labels = Object.keys(topicFrequency);
    topicPopularityChart.data.datasets[0].data = Object.values(topicFrequency);
    topicPopularityChart.update();
}

// Attach event listener to input field
document.getElementById("userInput").addEventListener("keypress", checkEnter);

