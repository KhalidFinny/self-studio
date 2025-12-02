export function initStatusPoller(statusUrl) {
    const countdownContainer = document.getElementById('countdown-container');
    const countdownText = document.getElementById('countdown-text');
    let lastFlashState = false;

    // Poll Backend Status for Gesture Trigger
    function updateStatus() {
        fetch(statusUrl)
            .then(response => response.json())
            .then(data => {
                // 1. Handle Countdown
                if (data.message && data.message !== "Saved Locally!" && data.message !== "Capture Failed!") {
                    countdownContainer.classList.remove('hidden');
                    if (countdownText.innerText !== data.message) {
                        countdownText.innerText = data.message;
                        countdownText.classList.remove('countdown-text');
                        void countdownText.offsetWidth;
                        countdownText.classList.add('countdown-text');
                    }
                } else {
                    countdownContainer.classList.add('hidden');
                }

                // 2. Handle Capture Trigger (Flash)
                // When backend says "flash", we trigger the Frontend AR Capture
                // Only trigger if state changed from false to true (rising edge)
                if (data.flash && !lastFlashState) {
                    console.log("Gesture detected! Triggering AR capture...");
                    if (window.takePhoto) {
                        window.takePhoto(); // Defined in ar_logic.js
                    }
                }
                lastFlashState = data.flash;
            })
            .catch(err => console.error("Error fetching status:", err));
    }

    setInterval(updateStatus, 100);
}
