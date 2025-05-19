async function checkStatus() {
    const statusDot = document.getElementById('status-dot');
    try {
        const response = await fetch('/api/tweets', { method: 'HEAD' });
        if (response.ok) {
            statusDot.classList.remove('bg-red-500');
            statusDot.classList.add('bg-green-500');
        } else {
            statusDot.classList.remove('bg-green-500');
            statusDot.classList.add('bg-red-500');
        }
    } catch (error) {
        statusDot.classList.remove('bg-green-500');
        statusDot.classList.add('bg-red-500');
    }
}

async function fetchTweets() {
    try {
        const loading = document.getElementById('loading');
        loading.textContent = 'Loading...';
        console.log('Fetching tweets from /api/tweets');

        const response = await fetch('/api/tweets');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const tweets = await response.json();
        console.log('Received tweets:', tweets);

        const tweetsContainer = document.getElementById('tweets');
        const tweetCount = document.getElementById('tweet-count');
        const statusDot = document.getElementById('status-dot');

        // Update status dot on successful fetch
        statusDot.classList.remove('bg-red-500');
        statusDot.classList.add('bg-green-500');

        // Sort tweets by created_at (newest first)
        tweets.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        loading.style.display = 'none';
        tweetsContainer.innerHTML = tweets.map(tweet => renderTweetRow(tweet)).join('');
        tweetCount.textContent = `Showing ${tweets.length} of ${tweets.length} tweets (max 100)`;

        function renderTweetRow(tweet) {
            console.log('Rendering tweet:', tweet.id, tweet.text);
            const timeDiff = (new Date() - new Date(tweet.created_at)) / 1000 / 60; // Minutes ago
            const timeText = timeDiff < 1 ? 'Just now' : `${Math.floor(timeDiff)} minute${Math.floor(timeDiff) === 1 ? '' : 's'} ago`;
            const isNew = timeDiff < 5; // Mark as NEW if <5 minutes old
            const followers = tweet.user.followers_count >= 1000000 ? 
                `${(tweet.user.followers_count / 1000000).toFixed(1)}M` : 
                tweet.user.followers_count >= 1000 ? 
                `${(tweet.user.followers_count / 1000).toFixed(1)}K` : 
                tweet.user.followers_count;

            return `
                <tr class="border-t hover:bg-gray-600">
                    <td class="p-3">
                        ${timeText}${isNew ? '<span class="ml-2 text-xs text-blue-300 font-semibold">NEW</span>' : ''}
                    </td>
                    <td class="p-3">
                        <div class="flex items-center space-x-2">
                            <img src="${tweet.user.profile_image_url}" alt="Profile" class="w-6 h-6 rounded-full">
                            <div>
                                <p class="text-sm font-semibold text-gray-100">${tweet.user.name}</p>
                                <p class="text-xs text-gray-400">@${tweet.user.username}</p>
                            </div>
                        </div>
                    </td>
                    <td class="p-3">
                        <a href="${tweet.url}" target="_blank" class="text-sm text-blue-300 hover:text-blue-200">${tweet.text}</a>
                    </td>
                    <td class="p-3">${followers}</td>
                    <td class="p-3 flex justify-center">
                        <span class="w-2 h-2 rounded-full ${tweet.user.verified ? 'bg-green-500' : 'bg-red-500'} inline-block"></span>
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error fetching tweets:', error);
        document.getElementById('loading').textContent = 'Error loading tweets. Retrying...';
        const statusDot = document.getElementById('status-dot');
        statusDot.classList.remove('bg-green-500');
        statusDot.classList.add('bg-red-500');
    }
}

// Check status and fetch tweets initially and every 5 seconds
checkStatus();
fetchTweets();
setInterval(() => {
    checkStatus();
    fetchTweets();
}, 5000);